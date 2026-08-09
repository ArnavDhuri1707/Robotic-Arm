#!/usr/bin/env python3
# arm_mimic.py  --  Mode 1: MediaPipe arm mimicry (PC side)
#
# Tracks your arm with a webcam and streams six target joint angles to the
# ESP32 over UDP. Joints (in transmit order):
#     base, shoulder, elbow, wrist-rotation, wrist-flex, gripper
#
#   python arm_mimic.py                 # use settings from config.py
#   python arm_mimic.py --ip 192.168.1.77 --side left --no-window
#
# Press 'q' in the video window to quit.
#
# The angle math is intentionally approximate: mapping a human arm onto a
# 5-DOF servo arm is not exact. Use the on-screen RAW numbers to calibrate the
# *_MAP ranges in config.py (see the README).

import argparse
import math
import socket
import time

import cv2
import numpy as np
import mediapipe as mp

import config

mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
PL = mp_pose.PoseLandmark

# Hand pinch tuning (ratio of thumb-index tip distance to palm length).
GRIP_CLOSE_RATIO = 0.20   # at/below this -> fully closed (grip = 1.0)
GRIP_OPEN_RATIO = 1.10    # at/above this -> fully open   (grip = 0.0)


# --------------------------------------------------------------- vector math
def vec(lm):
    return np.array([lm.x, lm.y, lm.z], dtype=float)


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def angle_between(a, b):
    """Angle between two vectors, in degrees (0..180)."""
    ca = np.dot(unit(a), unit(b))
    ca = max(-1.0, min(1.0, ca))
    return math.degrees(math.acos(ca))


def map_range(x, in_min, in_max, out_min, out_max):
    """Linear map with clamping to the OUTPUT range (handles inverted out)."""
    if in_max == in_min:
        t = 0.0
    else:
        t = (x - in_min) / (in_max - in_min)
    t = max(0.0, min(1.0, t))
    return out_min + t * (out_max - out_min)


# --------------------------------------------------------------- filtering --
class _LowPass:
    """First-order low-pass with an externally supplied alpha."""

    def __init__(self):
        self.y = None

    def __call__(self, x, alpha):
        self.y = x if self.y is None else alpha * x + (1.0 - alpha) * self.y
        return self.y

    def reset(self):
        self.y = None


class OneEuroFilter:
    """Adaptive low-pass filter (Casiez, Roussel & Vogel, CHI 2012).

    Smooths hard when the signal is nearly still and backs off when it moves
    quickly, so the servos sit steady at rest without feeling laggy in motion.
    A plain exponential filter has to pick one or the other.

    min_cutoff : lower  -> steadier at rest, more lag
    beta       : higher -> less lag during fast motion
    """

    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._x = _LowPass()
        self._dx = _LowPass()
        self._prev = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self):
        self._x.reset()
        self._dx.reset()
        self._prev = None

    def __call__(self, x, dt):
        if dt <= 0.0:
            dt = 1e-3
        # Rate of change, itself low-passed so one noisy frame can't spike it.
        raw_dx = 0.0 if self._prev is None else (x - self._prev) / dt
        self._prev = x
        dx_hat = self._dx(raw_dx, self._alpha(self.d_cutoff, dt))
        # Faster motion -> higher cutoff -> less smoothing.
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        return self._x(x, self._alpha(cutoff, dt))


# --------------------------------------------------------------- body frame -
def side_indices(side):
    if side == "left":
        return dict(sh=PL.LEFT_SHOULDER, el=PL.LEFT_ELBOW, wr=PL.LEFT_WRIST,
                    ix=PL.LEFT_INDEX, hip=PL.LEFT_HIP,
                    osh=PL.RIGHT_SHOULDER, ohip=PL.RIGHT_HIP)
    return dict(sh=PL.RIGHT_SHOULDER, el=PL.RIGHT_ELBOW, wr=PL.RIGHT_WRIST,
                ix=PL.RIGHT_INDEX, hip=PL.RIGHT_HIP,
                osh=PL.LEFT_SHOULDER, ohip=PL.LEFT_HIP)


def compute_arm_angles(world_lms, side):
    """Return raw human angles (deg) for base, shoulder, elbow, wristfl.
    Uses metric world landmarks and a body-relative coordinate frame so the
    result does not depend on camera orientation."""
    idx = side_indices(side)
    L = world_lms.landmark

    sh = vec(L[idx["sh"]]); el = vec(L[idx["el"]]); wr = vec(L[idx["wr"]])
    ix = vec(L[idx["ix"]]); hip = vec(L[idx["hip"]])
    osh = vec(L[idx["osh"]]); ohip = vec(L[idx["ohip"]])

    # Orthonormal body frame
    mid_sh = (sh + osh) / 2.0
    mid_hip = (hip + ohip) / 2.0
    up = unit(mid_sh - mid_hip)                 # torso up
    across = unit(sh - osh)                      # toward tracked side
    forward = unit(np.cross(across, up))         # out of chest
    across = unit(np.cross(up, forward))         # re-orthogonalize

    upper = el - sh          # shoulder -> elbow
    fore = wr - el           # elbow -> wrist
    hand = ix - wr           # wrist -> fingertip

    def elevation(v):
        """Angle above the horizontal plane, signed (deg)."""
        vertical = np.dot(v, up)
        horiz = math.hypot(np.dot(v, across), np.dot(v, forward))
        return math.degrees(math.atan2(vertical, horiz))

    # base: horizontal azimuth of the upper arm (side <-> forward)
    base = math.degrees(math.atan2(np.dot(upper, forward), np.dot(upper, across)))

    # shoulder: elevation of upper arm, 0 = hanging down, 180 = overhead
    shoulder = angle_between(upper, -up)

    # elbow: flexion between upper arm and forearm, 0 = straight
    elbow = angle_between(upper, fore)

    # wrist flex: how far the hand pitches relative to the forearm
    wristfl = elevation(hand) - elevation(fore)

    return {"base": base, "shoulder": shoulder, "elbow": elbow, "wristfl": wristfl}


# --------------------------------------------------------------- hands ------
def pick_hand(hands_result, pose_lms, side, w, h):
    """Choose the detected hand nearest the tracked pose wrist."""
    if not hands_result.multi_hand_landmarks:
        return None
    idx = side_indices(side)
    pw = pose_lms.landmark[idx["wr"]]
    target = np.array([pw.x * w, pw.y * h])
    best, best_d = None, 1e18
    for hlm in hands_result.multi_hand_landmarks:
        wrist = hlm.landmark[0]
        d = np.linalg.norm(np.array([wrist.x * w, wrist.y * h]) - target)
        if d < best_d:
            best_d, best = d, hlm
    return best


def compute_grip_and_roll(hlm):
    """Return (grip 0..1 closed, wrist_roll_deg) from a hand landmark set."""
    def p(i):
        return np.array([hlm.landmark[i].x, hlm.landmark[i].y])

    thumb_tip, index_tip = p(4), p(8)
    wrist, index_mcp, pinky_mcp = p(0), p(5), p(17)

    palm = np.linalg.norm(index_mcp - wrist) + 1e-6
    ratio = np.linalg.norm(thumb_tip - index_tip) / palm
    grip = 1.0 - map_range(ratio, GRIP_CLOSE_RATIO, GRIP_OPEN_RATIO, 0.0, 1.0)

    across = pinky_mcp - index_mcp          # image coords (y is down)
    roll = math.degrees(math.atan2(-across[1], across[0]))
    return grip, roll


# --------------------------------------------------------------- main -------
def main():
    ap = argparse.ArgumentParser(description="MediaPipe arm mimicry -> ESP32")
    ap.add_argument("--ip", default=config.ESP32_IP)
    ap.add_argument("--port", type=int, default=config.ESP32_PORT)
    ap.add_argument("--side", default=config.ARM_SIDE, choices=["left", "right"])
    ap.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    ap.add_argument("--no-window", action="store_true")
    ap.add_argument("--no-hands", action="store_true")
    args = ap.parse_args()

    use_hands = config.USE_HANDS and not args.no_hands
    show = config.SHOW_WINDOW and not args.no_window

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.ip, args.port)
    print("Streaming to {}:{}  (side={})".format(args.ip, args.port, args.side))

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera index {}".format(args.camera))

    pose = mp_pose.Pose(model_complexity=1, smooth_landmarks=True,
                        min_detection_confidence=0.6, min_tracking_confidence=0.6)
    hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5,
                           min_tracking_confidence=0.5) if use_hands else None

    # One filter per joint, each tuned in config.FILTER for how noisy that
    # joint's underlying signal is (see the notes in config.py).
    filters = {}
    for _name in config.JOINT_ORDER:
        _p = config.FILTER.get(_name, {})
        filters[_name] = OneEuroFilter(min_cutoff=_p.get("min_cutoff", 1.0),
                                       beta=_p.get("beta", 0.0))

    smoothed = None                       # filtered servo angles
    sent = None                           # last values actually sent (deadbanded)
    grip_val = 0.0                        # last known gripper (0 open..1 closed)
    roll_val = 0.0                        # last known wrist roll (deg)
    send_period = 1.0 / max(1, config.SEND_HZ)
    last_send = 0.0
    last_frame = 0.0                      # timestamp of last frame WITH tracking

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            if config.MIRROR:
                frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False

            pres = pose.process(rgb)
            hres = hands.process(rgb) if hands else None

            raw = None
            picked_hand = None
            if pres.pose_world_landmarks and pres.pose_landmarks:
                idx = side_indices(args.side)
                vis = min(pres.pose_landmarks.landmark[idx["sh"]].visibility,
                          pres.pose_landmarks.landmark[idx["el"]].visibility,
                          pres.pose_landmarks.landmark[idx["wr"]].visibility)
                if vis > 0.5:
                    raw = compute_arm_angles(pres.pose_world_landmarks, args.side)

                    if hres is not None:
                        hlm = pick_hand(hres, pres.pose_landmarks, args.side, w, h)
                        if hlm is not None:
                            grip_val, roll_val = compute_grip_and_roll(hlm)
                            picked_hand = hlm
                    raw["gripper"] = grip_val
                    raw["wristrot"] = roll_val

            if raw is not None:
                # Map raw human values -> servo degrees
                targets = {}
                for name in config.JOINT_ORDER:
                    m = config.JOINT_MAP[name]
                    targets[name] = map_range(
                        raw[name], m["human_min"], m["human_max"],
                        m["servo_min"], m["servo_max"])

                now = time.time()

                # If we lost the arm for a while, start the filters fresh so
                # they don't interpolate across the gap and lurch the servos.
                if last_frame and (now - last_frame) > config.FILTER_RESET_AFTER:
                    for f in filters.values():
                        f.reset()
                    sent = None
                    dt = 0.0
                else:
                    dt = now - last_frame if last_frame else 0.0
                last_frame = now

                smoothed = [filters[n](targets[n], dt)
                            for n in config.JOINT_ORDER]

                # Deadband: hold each joint until its target shifts more than
                # that joint's DEADBAND, so residual noise doesn't jitter the
                # servos. We still send every frame, so the ESP32 failsafe
                # never trips.
                if sent is None:
                    sent = list(smoothed)
                else:
                    for i, name in enumerate(config.JOINT_ORDER):
                        if abs(smoothed[i] - sent[i]) >= config.DEADBAND.get(name, 0.0):
                            sent[i] = smoothed[i]

                if now - last_send >= send_period:
                    msg = "S," + ",".join(str(int(round(v))) for v in sent)
                    sock.sendto(msg.encode(), dest)
                    last_send = now

            if show:
                if pres.pose_landmarks:
                    mp_draw.draw_landmarks(
                        frame, pres.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                if picked_hand is not None:
                    mp_draw.draw_landmarks(
                        frame, picked_hand, mp_hands.HAND_CONNECTIONS)
                    tt = picked_hand.landmark[4]   # thumb tip
                    it = picked_hand.landmark[8]   # index-finger tip
                    p1 = (int(tt.x * w), int(tt.y * h))
                    p2 = (int(it.x * w), int(it.y * h))
                    cv2.circle(frame, p1, 9, (255, 0, 255), -1)
                    cv2.circle(frame, p2, 9, (255, 0, 255), -1)
                    cv2.line(frame, p1, p2, (255, 0, 255), 2)
                    cv2.putText(frame, "claw {}%".format(int(round(grip_val * 100))),
                                ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2 - 12),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2,
                                cv2.LINE_AA)
                y = 24
                if raw is not None:
                    for name in config.JOINT_ORDER:
                        txt = "{:9s} raw={:7.1f}  servo={:5.1f}".format(
                            name, raw[name],
                            smoothed[config.JOINT_ORDER.index(name)]
                            if smoothed else 0.0)
                        cv2.putText(frame, txt, (10, y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                    (0, 255, 0), 1, cv2.LINE_AA)
                        y += 22
                else:
                    cv2.putText(frame, "No arm detected", (10, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow("Arm mimic (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()
        pose.close()
        if hands:
            hands.close()
        sock.close()


if __name__ == "__main__":
    main()

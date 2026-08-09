#!/usr/bin/env python3
"""minimal_mimic.py -- the smallest thing that tracks your elbow.

No filtering, no hands, no servo mapping, no networking, no config file.
Camera in, one number out. Everything in arm_mimic.py is this plus layers.

    python minimal_mimic.py          # press q to quit

Try to retype this from scratch rather than reading it. The ladder at the
bottom of the file is the order to build the rest back up in.
"""

import math

import cv2
import numpy as np
import mediapipe as mp

PL = mp.solutions.pose.PoseLandmark

SIDE = "left"        # which of YOUR arms to track: "left" or "right"
CAMERA = 0           # webcam index


def vec(lm):
    """One MediaPipe landmark -> a 3D numpy vector."""
    return np.array([lm.x, lm.y, lm.z], dtype=float)


def angle_between(a, b):
    """Angle between two vectors, in degrees (0..180).

    cos(theta) = (a . b) / (|a| |b|). The clamp matters: floating point can
    hand acos() something like 1.0000001 and it will raise a domain error.
    """
    cos = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def elbow_angle(world_landmarks):
    """Elbow flexion: 0 deg = arm straight, ~150 deg = hand at shoulder.

    Note this uses pose_WORLD_landmarks (metric, origin at the hips), not
    pose_landmarks (normalized image coords). Angles need real proportions.

    Elbow flexion is the one joint that needs no body frame: it is the angle
    between two segments of the arm itself, so it is already relative to you
    rather than to the camera. Every other joint needs the torso basis --
    that is the first thing you will add.
    """
    L = world_landmarks.landmark
    if SIDE == "left":
        sh, el, wr = L[PL.LEFT_SHOULDER], L[PL.LEFT_ELBOW], L[PL.LEFT_WRIST]
    else:
        sh, el, wr = L[PL.RIGHT_SHOULDER], L[PL.RIGHT_ELBOW], L[PL.RIGHT_WRIST]

    upper = vec(el) - vec(sh)        # shoulder -> elbow
    fore = vec(wr) - vec(el)         # elbow -> wrist
    return angle_between(upper, fore)


def main():
    cap = cv2.VideoCapture(CAMERA)
    if not cap.isOpened():
        raise RuntimeError("could not open camera {}".format(CAMERA))

    pose = mp.solutions.pose.Pose(model_complexity=1,
                                  min_detection_confidence=0.6,
                                  min_tracking_confidence=0.6)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)                   # selfie view
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # MediaPipe wants RGB

            res = pose.process(rgb)

            if res.pose_world_landmarks:
                ang = elbow_angle(res.pose_world_landmarks)
                print("elbow {:6.1f}".format(ang), end="\r")
                cv2.putText(frame, "elbow {:.0f}".format(ang), (10, 44),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 2,
                            cv2.LINE_AA)
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, res.pose_landmarks,
                    mp.solutions.pose.POSE_CONNECTIONS)
            else:
                cv2.putText(frame, "no pose", (10, 44),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2,
                            cv2.LINE_AA)

            cv2.imshow("minimal mimic (q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        pose.close()


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- the ladder
# Add one rung at a time. Run it after each. Do not skip ahead -- each rung
# fails in a way that teaches you why the next one exists.
#
# 1. Watch the number while you move. Notice it is jumpy by a few degrees even
#    when you hold still, and that it gets much worse when your arm points
#    toward or away from the camera. That is MediaPipe's z estimate. It is the
#    single biggest source of error in this whole project.
#
# 2. Add the torso frame: up = mid_shoulder - mid_hip, across = sh - other_sh,
#    forward = cross(across, up), then re-orthogonalize across. Print shoulder
#    elevation, angle_between(upper, -up), and confirm it stays stable while
#    you rotate your body. Without the frame it will not.
#
# 3. Add base rotation, atan2(dot(upper, forward), dot(upper, across)). Watch
#    how much noisier it is than the other two, and why: its axis IS depth.
#
# 4. Map one joint to servo degrees with a linear map + clamp. Find the input
#    range by moving your arm to its limits and reading the printed numbers.
#    Guessing these never works.
#
# 5. Send it to the ESP32 over UDP and drive one servo. Expect audible buzzing.
#
# 6. Add smoothing to stop the buzzing. Try a plain exponential filter first
#    (y = a*x + (1-a)*y) and convince yourself it forces a bad tradeoff:
#    steady at rest OR responsive in motion, never both. Then One Euro.
#
# 7. Add a deadband for the jitter that survives, and a filter reset for when
#    you step out of frame -- otherwise the servos lurch when you step back in.
#
# 8. Add MediaPipe Hands for the gripper: thumb tip (4) to index tip (8),
#    divided by palm length (wrist 0 to index MCP 5) so it is scale-invariant.
#
# At rung 8 you have rebuilt arm_mimic.py.

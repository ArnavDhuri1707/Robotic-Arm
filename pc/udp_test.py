#!/usr/bin/env python3
# udp_test.py -- exercise the WiFi + servo chain WITHOUT the webcam.
#
# Streams target poses to the ESP32 over UDP in the same packet format as
# arm_mimic.py ("S,a0,a1,a2,a3,a4,a5"), wiggling one joint at a time so you
# can confirm each joint receives packets and moves -- before adding MediaPipe.
#
#   py udp_test.py                     # uses ESP32_IP/PORT from config.py
#   py udp_test.py --ip 10.0.0.96      # override IP
#   py udp_test.py --seconds 20        # auto-stop after 20s (0 = run forever)
#
# Needs only the Python standard library + config.py (no opencv/mediapipe),
# so any Python works. Ctrl-C to stop; the arm returns home via its failsafe.

import argparse
import math
import socket
import time

import config


def build_packet(angles):
    return ("S," + ",".join(str(int(round(a))) for a in angles)).encode()


def main():
    ap = argparse.ArgumentParser(description="UDP servo test (no webcam)")
    ap.add_argument("--ip", default=config.ESP32_IP)
    ap.add_argument("--port", type=int, default=config.ESP32_PORT)
    ap.add_argument("--hz", type=int, default=25)
    ap.add_argument("--seconds", type=float, default=0.0,
                    help="auto-stop after N seconds (0 = forever)")
    args = ap.parse_args()

    order = config.JOINT_ORDER
    ranges = {}
    centers = {}
    for name in order:
        m = config.JOINT_MAP[name]
        lo, hi = sorted((m["servo_min"], m["servo_max"]))
        ranges[name] = (lo, hi)
        centers[name] = (lo + hi) / 2.0

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.ip, args.port)
    period = 1.0 / max(1, args.hz)
    print("Streaming test poses to {}:{}  ({} Hz, Ctrl-C to stop)".format(
        dest[0], dest[1], args.hz))

    t0 = time.time()
    last_j = -1
    try:
        while True:
            t = time.time() - t0
            if args.seconds > 0 and t >= args.seconds:
                break
            j = int(t // 3) % len(order)         # switch joint every 3 s
            if j != last_j:
                print("  wiggling joint {}: {}".format(j, order[j]))
                last_j = j
            angles = []
            for k, name in enumerate(order):
                lo, hi = ranges[name]
                a = centers[name]
                if k == j:
                    amp = (hi - lo) * 0.35
                    a = a + amp * math.sin(2 * math.pi * 0.5 * t)
                angles.append(max(lo, min(hi, a)))
            sock.sendto(build_packet(angles), dest)
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        # park at centers so the arm settles
        centers_pose = [centers[n] for n in order]
        sock.sendto(build_packet(centers_pose), dest)
        sock.close()


if __name__ == "__main__":
    main()

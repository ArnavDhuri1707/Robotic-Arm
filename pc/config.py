# config.py  --  PC-side settings for MediaPipe arm mimicry
#
# This file controls the network target, which arm to track, and how raw
# human joint angles are mapped onto your servo travel. Tune the *_MAP ranges
# during calibration (see README).

# ---------------------------------------------------------------- Network ---
# IP address the ESP32 printed on its serial console after connecting to WiFi.
ESP32_IP = "10.0.0.96"   # <-- change to your ESP32's IP
ESP32_PORT = 4210

# How many angle packets to send per second. 25-30 matches webcam framerate.
SEND_HZ = 25

# ---------------------------------------------------------------- Tracking --
# Which of YOUR arms to mimic: "right" or "left".
ARM_SIDE = "left"

# Webcam index (0 is usually the built-in / first camera).
CAMERA_INDEX = 0

# Mirror the webcam image (selfie view). Most people find True more intuitive.
MIRROR = True

# Use MediaPipe Hands for a reliable gripper + wrist-rotation signal.
# If False, the gripper is estimated from coarse pose points and wrist
# rotation is held at center.
USE_HANDS = True

# ---------------------------------------------------------------- Filtering -
# (These replace the old scalar SMOOTHING / DEADBAND_DEG settings.)
#
# Joint angles are filtered with a One Euro filter, which adapts to how fast
# you are moving: heavy smoothing while you hold still (kills resting jitter),
# light smoothing while you move fast (kills lag). This beats plain exponential
# smoothing, which forces you to pick one fixed point on that tradeoff.
#
# Per joint:
#   min_cutoff : LOWER  = steadier at rest, but more lag.  Tune this FIRST.
#   beta       : HIGHER = less lag during fast motion.     Tune this SECOND.
#
# How to tune, one joint at a time, watching the on-screen numbers:
#   1. Set beta = 0. Lower min_cutoff until the joint stops twitching at rest.
#   2. Raise beta until fast motion no longer feels delayed.
#
# Why the values differ per joint: joints derived from MediaPipe's depth (z)
# estimate are much noisier than ones derived from image x/y.
#   base     - its axis IS the depth direction. Noisiest joint by far.
#   wristfl  - built from a very short vector (wrist->index), which amplifies
#              noise, and from a difference of two angles, which compounds it.
#   elbow    - moderate; depends on z only when you bend toward the camera.
#   shoulder - fairly robust (acos is least sensitive near 90 degrees).
#   wristrot - computed from 2D image coords only. Already clean.
#   gripper  - 2D only as well, and wants to feel instant.
FILTER = {
    "base":     {"min_cutoff": 0.6, "beta": 0.020},
    "shoulder": {"min_cutoff": 1.0, "beta": 0.010},
    "elbow":    {"min_cutoff": 1.0, "beta": 0.015},
    "wristrot": {"min_cutoff": 1.5, "beta": 0.010},
    "wristfl":  {"min_cutoff": 0.7, "beta": 0.015},
    "gripper":  {"min_cutoff": 2.0, "beta": 0.020},
}

# Deadband (degrees of servo travel): a joint won't move until its target
# shifts more than this, which kills whatever jitter survives the filter.
# Higher = steadier but coarser. 0 disables. Noisy joints want a bigger number.
DEADBAND = {
    "base":     5.0,
    "shoulder": 2.0,
    "elbow":    2.0,
    "wristrot": 1.5,
    "wristfl":  3.0,
    "gripper":  2.0,
}

# If the arm goes undetected for longer than this (seconds), reset the filters
# so the servos don't lurch when you step back into frame.
FILTER_RESET_AFTER = 0.5

# ---------------------------------------------------------------- Mapping ---
# Each joint maps a HUMAN angle range -> a SERVO angle range.
#   human_min, human_max : the raw range your body produces (degrees)
#   servo_min, servo_max : where those map on the servo (degrees, 0-180)
# Flip servo_min/servo_max to reverse a joint in software.
#
# Order MUST match the ESP32: base, shoulder, elbow, wristrot, wristflex, gripper
JOINT_MAP = {
    # base rotation: arm azimuth (pointing sideways -> forward)
    "base":     {"human_min": -70, "human_max": 70,  "servo_min": 0,   "servo_max": 180},
    # shoulder: arm elevation, 0 = hanging down, ~160 = raised overhead
    "shoulder": {"human_min": 0,   "human_max": 160, "servo_min": 15,  "servo_max": 165},
    # elbow: flexion (straight -> fully bent)
    "elbow":    {"human_min": 0,   "human_max": 150, "servo_min": 0,   "servo_max": 150},
    # wrist rotation: forearm/hand roll
    "wristrot": {"human_min": -90, "human_max": 90,  "servo_min": 0,   "servo_max": 180},
    # wrist flex: hand up/down relative to forearm
    "wristfl":  {"human_min": -60, "human_max": 60,  "servo_min": 0,   "servo_max": 180},
    # gripper: pinch amount (open -> closed). Human value is 0..1, not degrees.
    "gripper":  {"human_min": 0.0, "human_max": 1.0, "servo_min": 90,  "servo_max": 10},
}

# Order the six joints are transmitted in (do not reorder without matching ESP32).
JOINT_ORDER = ["base", "shoulder", "elbow", "wristrot", "wristfl", "gripper"]

# Show the annotated camera window with live angles. Set False for headless.
SHOW_WINDOW = True

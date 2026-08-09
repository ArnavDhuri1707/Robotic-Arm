# servo_test.py -- bench / calibration helper for the robotic arm.
#
# Runs on the ESP32 (MicroPython). Import it at the REPL to jog servos,
# center them for assembly, and spot bad / continuous-rotation servos.
#
# USAGE (arm powered, external servo supply ON):
#   py -m mpremote connect COM7 resume repl
#   # press Ctrl-C to stop main.py, then:
#   >>> import servo_test as t
#   >>> t.info()          # print the channel + limits table
#   >>> t.center_all()    # every joint to its home angle -- do BEFORE attaching horns
#   >>> t.deg(1, 90)      # move joint 1 to 90 deg (respects limits + invert)
#   >>> t.home(3)         # send joint 3 to its home angle
#   >>> t.us(4, 1500)     # RAW: 1500us on channel 4 (range / continuous-servo test)
#   >>> t.sweep(2)        # slowly sweep joint 2 across its range
#   >>> t.release_all()   # relax all servos (stop holding torque)
#
# Joint index -> name (from config.SERVOS):
#   0 base   1 shoulder   2 elbow   3 wristrot   4 wristfl   5 gripper

import time
from machine import I2C, Pin

import config
from pca9685 import PCA9685

# --- hardware init (runs on import) ---
_i2c = I2C(config.I2C_ID, sda=Pin(config.I2C_SDA), scl=Pin(config.I2C_SCL),
           freq=config.I2C_FREQ)
pca = PCA9685(_i2c, address=config.PCA9685_ADDR)
pca.freq(config.SERVO_FREQ)

SERVOS = config.SERVOS


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _deg_to_us(s, d):
    if s["invert"]:
        d = 180.0 - d
    span = s["max_us"] - s["min_us"]
    return s["min_us"] + span * (d / 180.0)


def _set(i, d):
    s = SERVOS[i]
    d = _clamp(d, s["min_deg"], s["max_deg"])
    pca.set_us(s["channel"], int(_deg_to_us(s, d)))
    return d


def info():
    """Print each joint's index, name, channel, and limits."""
    for i, s in enumerate(SERVOS):
        print("[{}] {:8s} ch{}  deg {}-{}  home {}  us {}-{}  invert {}".format(
            i, s["name"], s["channel"], s["min_deg"], s["max_deg"],
            s["home_deg"], s["min_us"], s["max_us"], s["invert"]))


def deg(i, d):
    """Move joint i to d degrees (clamped to that joint's safe limits)."""
    d = _set(i, d)
    print("joint {} ({}) -> {} deg".format(i, SERVOS[i]["name"], d))


def home(i):
    """Send joint i to its home angle."""
    deg(i, SERVOS[i]["home_deg"])


def center_all():
    """Send every joint to its home angle. Do this before attaching horns."""
    for i in range(len(SERVOS)):
        home(i)
        time.sleep_ms(300)


def us(channel, microseconds):
    """RAW: send a pulse width (us) to a raw channel, ignoring limits.
    Use for range testing or spotting continuous-rotation servos
    (1500 = stop/center, 1000 & 2000 = opposite ends)."""
    pca.set_us(channel, microseconds)
    print("channel {} -> {} us".format(channel, microseconds))


def sweep(i, step=3, delay_ms=20):
    """Slowly sweep joint i from min to max and back to observe its travel."""
    s = SERVOS[i]
    lo, hi = s["min_deg"], s["max_deg"]
    for d in range(lo, hi + 1, step):
        _set(i, d); time.sleep_ms(delay_ms)
    for d in range(hi, lo - 1, -step):
        _set(i, d); time.sleep_ms(delay_ms)
    print("swept joint {} ({}) {}-{} deg".format(i, s["name"], lo, hi))


def release(i):
    """Relax joint i (stop sending pulses -> no holding torque)."""
    pca.release(SERVOS[i]["channel"])


def release_all():
    """Relax all joints."""
    for s in SERVOS:
        pca.release(s["channel"])


if __name__ == "__main__":
    info()
    print("Centering all joints to home...")
    center_all()

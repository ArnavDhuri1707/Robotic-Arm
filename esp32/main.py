# main.py  --  ESP32 (MicroPython) firmware for the 3D-printed robotic arm
#
# Mode 1: MediaPipe mimicry.
# The PC runs pose tracking and streams six target joint angles over WiFi/UDP.
# This firmware receives them, clamps + rate-limits each joint, and drives the
# servos through a PCA9685. On signal loss it returns to a safe home pose.
#
# Packet format (ASCII, one datagram per frame):
#     "S,a0,a1,a2,a3,a4,a5"
# where a0..a5 are integer degrees (0-180) for:
#     base, shoulder, elbow, wrist-rotation, wrist-flex, gripper.
# The leading "S" is a sanity marker; malformed packets are ignored.

import network
import socket
import time
from machine import I2C, Pin

import config
from pca9685 import PCA9685


# --------------------------------------------------------------- helpers ----
def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def deg_to_us(servo, deg):
    """Map a joint angle (deg) to a pulse width (us), honoring invert."""
    if servo["invert"]:
        deg = 180.0 - deg
    span_us = servo["max_us"] - servo["min_us"]
    return servo["min_us"] + span_us * (deg / 180.0)


# --------------------------------------------------------------- wifi -------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("WiFi: connecting to", config.WIFI_SSID)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                raise RuntimeError("WiFi connect timed out")
            time.sleep_ms(200)
    ip = wlan.ifconfig()[0]
    print("WiFi: connected, IP =", ip)
    return ip


# --------------------------------------------------------------- arm --------
class Arm:
    def __init__(self, pca, servos):
        self.pca = pca
        self.servos = servos
        # current + target angle per joint, both start at home
        self.current = [s["home_deg"] for s in servos]
        self.target = [s["home_deg"] for s in servos]
        for i in range(len(servos)):
            self._write(i, self.current[i])

    def _write(self, i, deg):
        s = self.servos[i]
        deg = clamp(deg, s["min_deg"], s["max_deg"])
        self.pca.set_us(s["channel"], int(deg_to_us(s, deg)))

    def set_targets(self, angles):
        for i, s in enumerate(self.servos):
            self.target[i] = clamp(angles[i], s["min_deg"], s["max_deg"])

    def go_home(self):
        for i, s in enumerate(self.servos):
            self.target[i] = s["home_deg"]

    def update(self):
        """Move each joint toward its target by at most MAX_STEP_DEG."""
        step = config.MAX_STEP_DEG
        for i in range(len(self.servos)):
            delta = self.target[i] - self.current[i]
            if delta > step:
                delta = step
            elif delta < -step:
                delta = -step
            if delta != 0:
                self.current[i] += delta
                self._write(i, self.current[i])


# --------------------------------------------------------------- parse ------
def parse_packet(data, n_joints):
    """Return a list of n_joints floats, or None if the packet is invalid."""
    try:
        text = data.decode().strip()
    except Exception:
        return None
    parts = text.split(",")
    if len(parts) != n_joints + 1 or parts[0] != "S":
        return None
    try:
        return [float(p) for p in parts[1:]]
    except ValueError:
        return None


# --------------------------------------------------------------- main -------
def main():
    # I2C + PCA9685
    i2c = I2C(config.I2C_ID, sda=Pin(config.I2C_SDA),
              scl=Pin(config.I2C_SCL), freq=config.I2C_FREQ)
    pca = PCA9685(i2c, address=config.PCA9685_ADDR)
    pca.freq(config.SERVO_FREQ)

    arm = Arm(pca, config.SERVOS)
    n = len(config.SERVOS)

    ip = connect_wifi()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.setblocking(False)
    print("UDP: listening on {}:{}".format(ip, config.UDP_PORT))
    print("Ready. Streaming target: {}:{}".format(ip, config.UDP_PORT))

    last_rx = time.ticks_ms()
    next_loop = time.ticks_ms()

    while True:
        # Drain the socket so we always act on the NEWEST frame (avoids lag).
        newest = None
        while True:
            try:
                data, _ = sock.recvfrom(128)
            except OSError:
                break
            if data:
                newest = data

        if newest is not None:
            angles = parse_packet(newest, n)
            if angles is not None:
                arm.set_targets(angles)
                last_rx = time.ticks_ms()

        # Failsafe: no data for too long -> return to home
        if config.FAILSAFE_MS > 0:
            if time.ticks_diff(time.ticks_ms(), last_rx) > config.FAILSAFE_MS:
                arm.go_home()

        # Fixed-rate servo update
        now = time.ticks_ms()
        if time.ticks_diff(now, next_loop) >= 0:
            arm.update()
            next_loop = time.ticks_add(now, config.LOOP_MS)
        else:
            time.sleep_ms(1)


if __name__ == "__main__":
    main()

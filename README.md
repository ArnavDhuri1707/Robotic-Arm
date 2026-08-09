# 3D-Printed Robotic Arm — Mode 1: MediaPipe Mimicry

Servo arm (5 DOF + gripper) driven by an **ESP32-D** running **MicroPython** and a
**PCA9685** servo controller. A PC tracks your arm with a webcam (MediaPipe) and
streams six target joint angles to the ESP32 over **WiFi/UDP**; the firmware
smooths and rate-limits the motion and drives the servos.

```
 Webcam ─▶ PC (arm_mimic.py, MediaPipe)  ──UDP angles──▶  ESP32 (main.py)
                                                             │ I2C
                                                             ▼
                                                          PCA9685 ──▶ 6 servos
```

Joint order everywhere: `base, shoulder, elbow, wrist-rotation, wrist-flex, gripper`.

## Files

```
esp32/                 (upload these to the ESP32 as MicroPython files)
  pca9685.py           minimal PCA9685 driver
  config.py            WiFi, pins, per-servo calibration, motion limits
  main.py              WiFi + UDP receiver + servo control loop
  servo_test.py        bench helper: center servos, jog joints, spot bad servos

pc/                    (run these on your computer)
  arm_mimic.py         webcam tracking -> UDP streamer
  udp_test.py          no-camera link test (streams poses straight to the arm)
  config.py            ESP32 IP, arm side, human->servo angle mapping
  requirements.txt     Python dependencies
  run_arm.bat          one-click: start the webcam mimic
  test_link.bat        one-click: run the no-camera link test
```

## Quick start (one-click)

Once everything is set up (see below), you don't need the terminal day-to-day:

- **`pc/run_arm.bat`** — double-click to start the webcam mimic. Raise your (left)
  arm in view of the camera; pinch thumb + index finger to work the gripper claw;
  press `q` in the video window to stop. For a desktop launcher, right-click the
  file → Show more options → Send to → Desktop (create shortcut).
- **`pc/test_link.bat`** — double-click to run the no-camera link test. The arm
  wiggles one joint at a time, proving WiFi + servos work without the camera. Run
  this first whenever the arm won't respond.

Both need the arm **powered on and on WiFi**. The launchers use Python 3.12; if a
window closes instantly, an error printed just above the prompt — read it.

## Wiring

The PCA9685 drives the servos; the ESP32 only sends it I2C commands. **Do not
power servos from the ESP32's 3.3 V pin.**

| PCA9685 pin | Connect to |
|-------------|------------|
| VCC (logic) | ESP32 3V3 |
| GND         | ESP32 GND **and** servo-supply GND (common ground is required) |
| SDA         | ESP32 GPIO 21 |
| SCL         | ESP32 GPIO 22 |
| V+ (servo power) | External **5–6 V** supply, sized for stall current |
| Servos      | Channels 0–5 in joint order (see below) |

Channel map (from `esp32/config.py`): `0 base, 1 shoulder, 2 elbow,
3 wrist-rotation, 4 wrist-flex, 5 gripper`.

Power notes: six hobby servos can pull several amps under load. Use a dedicated
5–6 V supply (a 5 V 3–5 A UBEC or bench supply is a safe start), add a large
electrolytic cap (≥1000 µF) across V+/GND at the PCA9685, and **tie all grounds
together**. USB from your PC cannot power the servos.

## ESP32 setup (MicroPython)

1. Flash MicroPython to the ESP32 (once):
   - Download the latest ESP32 build from micropython.org.
   - `pip install esptool`
   - `esptool.py --port COM5 erase_flash`
   - `esptool.py --port COM5 --baud 460800 write_flash -z 0x1000 esp32-XXXXX.bin`
     (use `/dev/ttyUSB0` instead of `COM5` on Linux/Mac; `0x1000` is correct for
     most ESP32-D modules.)
2. Edit `esp32/config.py`: set `WIFI_SSID` / `WIFI_PASSWORD`, and confirm the
   I2C pins and channel map.
3. Upload the three files in `esp32/` to the board with a tool like
   [Thonny](https://thonny.org) (recommended, easiest) or `mpremote`:
   ```
   mpremote connect COM5 fs cp esp32/pca9685.py :pca9685.py
   mpremote connect COM5 fs cp esp32/config.py  :config.py
   mpremote connect COM5 fs cp esp32/main.py    :main.py
   ```
4. Reset the board and watch the serial console. On success it prints:
   ```
   WiFi: connected, IP = 192.168.1.50
   UDP: listening on 192.168.1.50:4210
   ```
   **Note that IP** — you'll put it in the PC config.

`main.py` runs automatically on boot. On startup, and whenever it stops
receiving packets for `FAILSAFE_MS`, the arm returns to the `home_deg` pose.

## PC setup

1. Install **Python 3.11 or 3.12** (MediaPipe 0.10.14 has no wheels for 3.13+).
   On Windows the `py -3.12` launcher picks the right one. Then:
   ```
   cd pc
   py -3.12 -m pip install -r requirements.txt
   ```
2. Edit `pc/config.py`: set `ESP32_IP` to the address the board printed, and
   `ARM_SIDE` to the arm you want to mimic.
3. Run it — just double-click **`run_arm.bat`**, or from a terminal:
   ```
   py -3.12 arm_mimic.py
   ```
   A window shows your tracked skeleton with live `raw` (human) and `servo`
   angles; pinch thumb + index to work the gripper. Press `q` to quit. Handy flags:
   ```
   py -3.12 arm_mimic.py --ip 10.0.0.96 --side left
   py -3.12 arm_mimic.py --no-window        # headless
   py -3.12 arm_mimic.py --no-hands         # skip the Hands model (faster)
   ```

## Calibration (do this before trusting the mechanics)

Work in this order; keep the arm somewhere it can move freely and be ready to
cut servo power.

1. **Per-servo pulse range** (`esp32/config.py` `min_us`/`max_us`): the defaults
   (600–2400 µs) suit many servos but not all. Adjust so 0° and 180° match your
   servo's real travel without buzzing at the ends.
2. **Travel limits** (`min_deg`/`max_deg`): start narrow to protect your printed
   linkage, then widen. These are hard clamps the firmware never exceeds.
3. **Home pose** (`home_deg`): the safe pose used on boot and signal loss.
4. **Direction** (`invert`): if a joint moves the wrong way, flip `invert`
   (firmware) or swap `servo_min`/`servo_max` for that joint (PC config).
5. **Human→servo mapping** (`pc/config.py` `JOINT_MAP`): watch the on-screen
   `raw` numbers while you move. Set each joint's `human_min`/`human_max` to the
   range you actually produce, and `servo_min`/`servo_max` to the servo travel
   you want it mapped onto.
6. **Gripper feel**: tune `GRIP_CLOSE_RATIO` / `GRIP_OPEN_RATIO` at the top of
   `arm_mimic.py` so a full pinch closes and an open hand opens the gripper.

Safety: keep `MAX_STEP_DEG` low at first (caps servo speed), test with the arm
unloaded, and verify the failsafe by covering the camera — the arm should ease
back to home.

## Protocol

One UDP datagram per frame, ASCII:

```
S,<base>,<shoulder>,<elbow>,<wristrot>,<wristflex>,<gripper>
```

Each value is an integer degree (0–180). The `S` marker guards against
malformed packets. Change `UDP_PORT` in both configs together if you need a
different port.

## Troubleshooting

- **Arm doesn't move.** Run `test_link.bat` (or `py udp_test.py`) to test the
  link without the camera. Nine times out of ten it's the **servo supply switched
  off**, or the ESP32 got a **new IP** after a reboot — check its serial output
  and update `ESP32_IP` in `pc/config.py`.
- **Arm doesn't move, board shows an IP.** PC and ESP32 must be on the same
  network/subnet, and the PC's `ESP32_IP` must match. Some WiFi networks block
  device-to-device (UDP) traffic — try a phone hotspot to test.
- **Servos jitter or the board browns out.** Under-powered servo supply or no
  common ground. Add the cap, use a beefier 5–6 V supply, tie grounds.
- **A joint moves backwards or hits an end stop.** Fix with `invert` /
  `min_deg`/`max_deg` (firmware) before touching the mapping.
- **`mediapipe` won't install.** Use Python 3.11 or 3.12 — the project pins
  `mediapipe==0.10.14`, which has no wheels for 3.13+. Run the PC script with
  `py -3.12`. (If `mp.solutions` errors, you're on a too-new MediaPipe/Python.)
- **Tracking is laggy.** Run with `--no-hands`, lower `SEND_HZ`, or improve
  lighting so pose tracking stays locked.

## What's next (Mode 2)

Voice-command mode (speech recognition on the PC + a virtually trained policy)
reuses the same ESP32 firmware and UDP protocol — it just becomes another source
of the six joint angles. Ask when you're ready and we'll build it on top of this.

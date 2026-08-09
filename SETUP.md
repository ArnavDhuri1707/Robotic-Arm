# Building This Arm From Scratch

A start-to-finish guide to reproduce the whole thing on a fresh Windows PC and a
bare ESP32 — including all the traps that waste hours. Read the **Gotchas** boxes;
they are the actual things that went wrong.

> TL;DR of the pain: on Windows use `py`, not `python`. The CH340 ESP32 needs
> `mpremote ... resume`. MediaPipe only works on Python 3.11/3.12. And "nothing
> moves" is almost always the servo power supply being off or a changed IP.

---

## 0. What you need

**Hardware**

- ESP32-D dev board (this one has a **CH340** USB-serial chip)
- PCA9685 16-channel servo driver
- 4 × MG90S servos — **positional**, not continuous-rotation (see Gotcha in §3)
- 2 × DS3218 servos (270° version) for shoulder + elbow
- External **5–6 V** power supply for the servos, rated ~6 A or more
- Jumper wires, a USB cable, a webcam, and the 3D-printed arm parts

**Software (install these first)**

- **Python 3.12** — from python.org. On Windows this registers the `py` launcher.
  (MediaPipe has no wheels for 3.13/3.14, so you specifically need 3.11 or 3.12.)
- **Thonny** (optional, easiest GUI for flashing) — thonny.org
- **Git** (only if publishing to GitHub) — git-scm.com

---

## 1. Flash MicroPython onto the ESP32 (one-time)

The ESP32 ships blank. You put the MicroPython runtime on it once.

1. Plug the ESP32 into USB. If Windows doesn't see it, install the **CH340 driver**.
2. Find its COM port: `py -m pip install mpremote` then `py -m mpremote connect list`
   — the ESP32 is the line showing `1a86:7523 wch.cn`. Note the `COMx`.
3. Download the **ESP32_GENERIC** `.bin` from <https://micropython.org/download/ESP32_GENERIC/>.
4. Flash it (replace `COM7` and the filename):

   ```
   py -m pip install esptool
   py -m esptool --chip esp32 --port COM7 erase-flash
   py -m esptool --chip esp32 --port COM7 write-flash -z 0x1000 ESP32_GENERIC-XXXXXXXX-vX.XX.X.bin
   ```

> **Gotcha — `python` is not found:** Windows aliases `python` to a Store stub.
> Always use `py` (or `py -3.12`). Fix permanently in Settings → Apps → Advanced
> app settings → App execution aliases → turn off the python.exe aliases.
>
> **Gotcha — esptool can't connect:** hold the board's **BOOT/IO0** button, tap
> **EN/RST**, release BOOT, then rerun the flash command.
>
> **Gotcha — board boots but hangs (no `MicroPython` banner, or `invalid header:
> 0xffffffff` looping):** the flash didn't take. Re-run `erase-flash` then
> `write-flash`.

---

## 2. Configure and upload the firmware

1. Copy `esp32/config.example.py` to `esp32/config.py` and set `WIFI_SSID` /
   `WIFI_PASSWORD` (a **2.4 GHz** network — the ESP32 can't join 5 GHz).
2. Upload the four files to the board (run from the `esp32/` folder):

   ```
   py -m mpremote connect COM7 resume cp main.py pca9685.py config.py servo_test.py :
   ```

3. Reboot and read the IP it prints:

   ```
   py -m mpremote connect COM7 resume repl
   ```
   Press **EN/RST**. You want:
   ```
   WiFi: connected, IP = 10.0.0.96
   UDP: listening on 10.0.0.96:4210
   ```
   **Write that IP down** — it goes in the PC config. Exit the repl with **Ctrl+]**.

> **Gotcha — `could not enter raw repl`:** the CH340 resets the board when the
> port opens, so mpremote's handshake misses. The `resume` keyword fixes it — it's
> in every command above for a reason. Also: **close Thonny** first (only one
> program can hold the COM port).
>
> **Gotcha — the COM number changes** when you plug into a different USB socket.
> Re-run `py -m mpremote connect list` if commands stop finding the board.

`main.py` auto-runs on every boot. If it stops receiving packets for `FAILSAFE_MS`
(0.8 s), the arm eases back to its home pose.

---

## 3. Wire the hardware

| PCA9685 pin      | Connect to |
|------------------|------------|
| VCC (logic)      | ESP32 **3V3** |
| GND              | ESP32 **GND** *and* servo-supply **GND** (common ground is mandatory) |
| SDA              | ESP32 **GPIO 21** |
| SCL              | ESP32 **GPIO 22** |
| V+ (servo power) | External **5–6 V** supply |
| Channels 0–5     | Servos, in joint order below |

**Channel map:** `0 base (MG90S) · 1 shoulder (DS3218) · 2 elbow (DS3218) ·
3 wrist-rot (MG90S) · 4 wrist-flex (MG90S) · 5 gripper (MG90S)`.

Each channel has 3 pins: **PWM (signal), V+ (middle), GND**. Match the servo lead:
brown/black → GND, red → V+ (middle), orange/yellow → PWM. On an unlabeled board,
channel 0 is the group nearest the I2C input pins; if unsure, test which channel
moves a servo with `servo_test.py` (§4).

> **Gotcha — never power servos from the ESP32 or USB.** The DS3218s alone can pull
> 2–3 A each. Use the dedicated 5–6 V supply into V+, and tie **all grounds
> together** or the servos won't read the signal.
>
> **Gotcha — a servo just spins forever instead of holding a position.** That's a
> **continuous-rotation** servo (some MG90S are sold that way) or a dead one, not a
> wiring fault. Positional servos only. Test: at 1500 µs a good positional servo
> holds center; a continuous one spins.
>
> **The #1 "nothing moves" cause: the servo supply isn't switched on.** Check that
> first, every time.

---

## 4. Center the servos, then assemble

Before bolting horns/linkages on, drive every servo to its neutral pose so the
joints assemble square. With the board powered and on WiFi:

```
py -m mpremote connect COM7 resume repl
```
Press **Ctrl+C** to stop `main.py`, then:
```python
import servo_test as t
t.info()          # channel + limits table
t.center_all()    # every joint to its home angle -- do this BEFORE attaching horns
t.deg(1, 90)      # jog one joint (index 1 = shoulder) to a specific angle
t.sweep(2)        # slowly sweep a joint to see its travel
```

---

## 5. PC setup

1. In `pc/`, install the dependencies **into Python 3.12**:
   ```
   cd pc
   py -3.12 -m pip install -r requirements.txt
   ```
2. Copy the IP from §2 into `pc/config.py` → `ESP32_IP`, and set `ARM_SIDE`
   (`"left"` or `"right"`).

> **Gotcha — `mediapipe==0.10.14` won't install / `mp.solutions` errors:** you're
> on the wrong Python. It must be 3.11 or 3.12, and you must launch with `py -3.12`
> (not the default 3.14). Newer MediaPipe releases broke the Pose/Hands API, which
> is why the version is pinned.

---

## 6. Run it

- **Full webcam mimic:** double-click `pc/run_arm.bat`, or `py -3.12 arm_mimic.py`.
  Raise your arm; pinch thumb + index to work the gripper; press `q` to stop.
- **No-camera link test:** double-click `pc/test_link.bat`, or `py udp_test.py`.
  The arm wiggles one joint at a time — use this to prove WiFi + servos work
  independently of the camera.

> **Gotcha — nothing moves:** run the link test. If *that* is dead too, it's not
> the camera. Check, in order: (1) servo supply on, (2) the ESP32's current IP
> matches `pc/config.py` — it can change on reboot, (3) the PC is on the **same
> WiFi** as the arm. `ping <ESP32_IP>` from PowerShell: replies = it's the servo
> power; timeouts = wrong network.

---

## 7. Calibrate and tune

- **Servo travel** (`esp32/config.py` `min_us`/`max_us`, `min_deg`/`max_deg`):
  widen or narrow each joint's range; start conservative to protect the linkage.
  Editing these needs a re-upload (`py -m mpremote connect COM7 resume cp config.py :`).
- **Direction:** flip `invert` (firmware) or swap `servo_min`/`servo_max` (PC).
- **Human→servo mapping** (`pc/config.py` `JOINT_MAP`): watch the on-screen `raw`
  numbers and set each joint's `human_min`/`human_max` to the range you produce.
- **Gripper feel:** `GRIP_CLOSE_RATIO` / `GRIP_OPEN_RATIO` at the top of `arm_mimic.py`.
- **Stability (if it jitters):** tune `FILTER` and `DEADBAND` in `pc/config.py`
  (PC-side, just restart). Both are **per joint** — fix the joint that's actually
  twitching rather than dulling the whole arm. For a jittery joint, first lower
  its `min_cutoff`; if that makes it feel laggy, raise its `beta`. If it still
  quivers while you hold still, raise its `DEADBAND`. Failing all that, lower
  `MAX_STEP_DEG` in `esp32/config.py` (needs re-upload) so motion glides
  instead of snaps.
  > `base` is the twitchiest joint by design — its axis lines up with the
  > camera's depth direction, which is MediaPipe's least reliable output.
  > `wristfl` is second. Expect to give both of those more filtering than the rest.

---

## Publishing to GitHub

**Do upload:** all the code — `esp32/main.py`, `pca9685.py`, `servo_test.py`,
`config.example.py`; `pc/arm_mimic.py`, `udp_test.py`, `config.py`,
`requirements.txt`, `run_arm.bat`, `test_link.bat`; `README.md`, `SETUP.md`,
`.gitignore`. STL/3D files too if you have them.

**Do NOT upload:** your real `esp32/config.py` (it has your WiFi password),
`__pycache__/` folders, or any `venv/`. The included `.gitignore` already excludes
these — `esp32/config.py` is ignored, and `config.example.py` is committed in its
place so others can copy it.

> **Before your first push, double-check the password isn't going up:** run
> `git status` and confirm `esp32/config.py` is **not** in the list. If it ever
> was committed, changing the WiFi password is the only real fix — git history
> keeps old versions.

Steps (from the project root):

```
git init
git add .
git status                     # verify esp32/config.py is NOT listed
git commit -m "3D-printed robotic arm: MediaPipe mimic (Mode 1)"
```

Then make an empty repo on github.com (no README), and:

```
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Anyone cloning it then does: copy `esp32/config.example.py` → `esp32/config.py`,
fill in their WiFi, and follow this guide from §1.

---

## One-page cheat sheet

```
Flash MicroPython : py -m esptool --chip esp32 --port COM7 erase-flash
                    py -m esptool --chip esp32 --port COM7 write-flash -z 0x1000 <bin>
Upload firmware   : py -m mpremote connect COM7 resume cp main.py pca9685.py config.py servo_test.py :
See boot / get IP : py -m mpremote connect COM7 resume repl   (press EN/RST, Ctrl+] to exit)
Find COM port     : py -m mpremote connect list               (look for 1a86:7523)
PC deps           : py -3.12 -m pip install -r requirements.txt
Run mimic         : run_arm.bat      (or  py -3.12 arm_mimic.py)
Test link no cam  : test_link.bat    (or  py udp_test.py)
Nothing moves?    : servo power ON → ping the IP → same WiFi → IP matches config
```

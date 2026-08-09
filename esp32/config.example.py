# config.example.py  --  TEMPLATE for esp32/config.py
#
# Copy this file to  config.py  and fill in your own WiFi credentials before
# uploading to the ESP32. The real config.py is git-ignored so your password
# never gets committed. Everything else here is safe to share.

# ---------------------------------------------------------------- WiFi ------
WIFI_SSID = "YOUR_WIFI_SSID"          # 2.4 GHz network (ESP32 can't do 5 GHz)
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# UDP port the ESP32 listens on. The PC script must send to this port.
UDP_PORT = 4210

# ---------------------------------------------------------------- I2C -------
# Default ESP32 I2C pins. Change if you wired the PCA9685 elsewhere.
I2C_ID = 0
I2C_SDA = 21
I2C_SCL = 22
I2C_FREQ = 400000
PCA9685_ADDR = 0x40
SERVO_FREQ = 50  # Hz -- standard for analog/most digital hobby servos

# ---------------------------------------------------------------- Servos ----
# One entry per joint, in the ORDER the PC sends them:
#   0 base rotation, 1 shoulder, 2 elbow, 3 wrist rotation, 4 wrist flex, 5 gripper
#
# Fields per joint:
#   channel  : PCA9685 output channel (0-15) the servo is plugged into
#   min_us   : pulse width (microseconds) at 0 deg   -- CALIBRATE per servo
#   max_us   : pulse width (microseconds) at 180 deg -- CALIBRATE per servo
#   min_deg  : software lower travel limit (deg)  -- protects your linkage
#   max_deg  : software upper travel limit (deg)
#   home_deg : safe pose the arm moves to on boot / on signal loss
#   invert   : True flips direction if a joint moves the wrong way
#
# Typical SG90/MG90 span ~500-2500 us. MG996R often ~600-2400 us.
# Start with a NARROW min/max_deg and widen once you trust the mechanics.
SERVOS = [
    # name              channel min_us max_us min_deg max_deg home_deg invert
    {"name": "base",    "channel": 0, "min_us": 600, "max_us": 2400, "min_deg": 0,  "max_deg": 180, "home_deg": 90,  "invert": False},
    # ch1 & ch2 are DS3218 270-degree servos: NARROWER us band so the commanded
    # 0-180 maps onto a SAFE physical sweep (~7.41 us/deg). Widen only after test.
    {"name": "shoulder","channel": 1, "min_us": 500, "max_us": 1830, "min_deg": 15, "max_deg": 165, "home_deg": 90,  "invert": False},
    {"name": "elbow",   "channel": 2, "min_us": 500, "max_us": 1610, "min_deg": 0,  "max_deg": 150, "home_deg": 60,  "invert": False},
    {"name": "wristrot","channel": 3, "min_us": 600, "max_us": 2400, "min_deg": 0,  "max_deg": 180, "home_deg": 90,  "invert": False},
    {"name": "wristfl", "channel": 4, "min_us": 600, "max_us": 2400, "min_deg": 0,  "max_deg": 180, "home_deg": 90,  "invert": False},
    {"name": "gripper", "channel": 5, "min_us": 600, "max_us": 2400, "min_deg": 10, "max_deg": 90,  "home_deg": 30,  "invert": False},
]

# ---------------------------------------------------------------- Motion ----
# Max degrees a joint may move per control loop. Caps servo speed so the arm
# never slams to a new target. Lower = smoother/safer, higher = snappier.
MAX_STEP_DEG = 6.0

# Control loop period in milliseconds (how often servos are refreshed).
LOOP_MS = 20  # 50 Hz update

# Failsafe: if no packet arrives for this many ms, return to home pose.
# Set to 0 to disable (arm holds last commanded pose instead).
FAILSAFE_MS = 800

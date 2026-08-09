# pca9685.py
# Minimal MicroPython driver for the PCA9685 16-channel PWM/servo controller.
# Self-contained: no external dependencies beyond machine + time.
#
# Usage:
#   from machine import I2C, Pin
#   from pca9685 import PCA9685
#   i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)
#   pca = PCA9685(i2c)
#   pca.freq(50)                 # 50 Hz for hobby servos
#   pca.set_us(0, 1500)          # send 1500 us pulse to channel 0

import ustruct
import time


class PCA9685:
    # Register map
    _MODE1 = 0x00
    _PRESCALE = 0xFE
    _LED0_ON_L = 0x06

    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self._period_us = 20000  # updated by freq(); 50 Hz => 20000 us
        self.reset()

    def _write8(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value & 0xFF]))

    def _read8(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def reset(self):
        self._write8(self._MODE1, 0x00)
        time.sleep_ms(5)

    def freq(self, freq):
        """Set the PWM frequency in Hz (use 50 for hobby servos)."""
        self._period_us = int(1000000 // freq)
        prescale = int(25000000.0 / (4096.0 * freq) + 0.5) - 1
        old_mode = self._read8(self._MODE1)
        # Enter sleep to change prescale
        self._write8(self._MODE1, (old_mode & 0x7F) | 0x10)
        self._write8(self._PRESCALE, prescale)
        self._write8(self._MODE1, old_mode)
        time.sleep_ms(5)
        # Restart + auto-increment enabled
        self._write8(self._MODE1, old_mode | 0xA1)

    def set_pwm(self, channel, on, off):
        """Set raw 12-bit on/off counts (0..4095) for a channel."""
        self.i2c.writeto_mem(
            self.address,
            self._LED0_ON_L + 4 * channel,
            ustruct.pack("<HH", on & 0x0FFF, off & 0x0FFF),
        )

    def set_us(self, channel, microseconds):
        """Set the pulse width for a channel in microseconds."""
        if microseconds <= 0:
            self.set_pwm(channel, 0, 0)  # fully off (no pulse)
            return
        # 4096 counts span one PWM period
        off = int(microseconds * 4096 // self._period_us)
        if off < 1:
            off = 1
        if off > 4095:
            off = 4095
        self.set_pwm(channel, 0, off)

    def release(self, channel):
        """Stop driving a channel (servo goes limp)."""
        self.set_pwm(channel, 0, 0)

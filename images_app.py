#!/usr/bin/env python3
"""Simple image viewer for the 1.44 inch LCD."""
import os
import time

import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.lcd.device import st7735
from PIL import Image

# --- Display setup ---
RST_PIN = 27
DC_PIN = 25
LCD_WIDTH = 128
LCD_HEIGHT = 128

serial = spi(port=0, device=0, cs_high=False,
             gpio_DC=DC_PIN, gpio_RST=RST_PIN,
             speed_hz=16000000)

device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1)

# --- Button setup ---
GPIO.setmode(GPIO.BCM)
BUTTON_PINS = {
    "KEY3": 16,
    "JOY_LEFT": 5,
    "JOY_RIGHT": 26,
}
for pin in BUTTON_PINS.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- Load images ---
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(IMG_DIR, exist_ok=True)
images = [os.path.join(IMG_DIR, f) for f in os.listdir(IMG_DIR)
          if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]
images.sort()

if not images:
    # Generate simple placeholders if no images exist. This avoids bundling
    # binary files in the repository while still demonstrating functionality.
    from PIL import ImageDraw

    colors = ["red", "green", "blue"]
    for i, color in enumerate(colors, start=1):
        img = Image.new("RGB", (LCD_WIDTH, LCD_HEIGHT), color)
        draw = ImageDraw.Draw(img)
        draw.text((10, 60), f"Image {i}", fill="white")
        path = os.path.join(IMG_DIR, f"placeholder_{i}.png")
        img.save(path)
        images.append(path)

current_idx = 0

def show_image(idx: int) -> None:
    path = images[idx]
    img = Image.open(path).convert("RGB").resize((LCD_WIDTH, LCD_HEIGHT))
    device.display(img)

show_image(current_idx)

try:
    while True:
        if GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
            break
        if GPIO.input(BUTTON_PINS["JOY_LEFT"]) == GPIO.LOW:
            current_idx = (current_idx - 1) % len(images)
            show_image(current_idx)
            time.sleep(0.2)
        if GPIO.input(BUTTON_PINS["JOY_RIGHT"]) == GPIO.LOW:
            current_idx = (current_idx + 1) % len(images)
            show_image(current_idx)
            time.sleep(0.2)
        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    device.cleanup()
    GPIO.cleanup()

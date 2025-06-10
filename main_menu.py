#!/usr/bin/env python3
"""Simple menu for the Waveshare 1.44"""

import os
import subprocess
import time

import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont


# --- Display setup ---
RST_PIN = 27
DC_PIN = 25
LCD_WIDTH = 128
LCD_HEIGHT = 128

serial = spi(port=0, device=0, cs_high=False,
             gpio_DC=DC_PIN, gpio_RST=RST_PIN,
             speed_hz=16000000)

device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1)

try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", 12)
except IOError:
    font = ImageFont.load_default()

# --- Button/Joystick setup ---
GPIO.setmode(GPIO.BCM)
BUTTON_PINS = {
    "KEY1": 21,
    "KEY2": 20,
    "KEY3": 16,
    "JOY_UP": 6,
    "JOY_DOWN": 19,
    "JOY_LEFT": 5,
    "JOY_RIGHT": 26,
    "JOY_PRESS": 13,
}

for pin in BUTTON_PINS.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def reinitialize():
    """Reinitialize display and GPIO after running another script."""
    global serial, device
    serial = spi(port=0, device=0, cs_high=False,
                 gpio_DC=DC_PIN, gpio_RST=RST_PIN,
                 speed_hz=16000000)
    device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1)
    GPIO.setmode(GPIO.BCM)
    for pin in BUTTON_PINS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


MENU_ITEMS = [
    ("LCD Demo", "test_144_lcd.py"),
    ("Input Demo", "test_screen_buttons_joystick.py"),
    ("Snake Game", "snake_game.py"),
    ("IRC Chat", "irc_chat.py"),
    ("Remote Server", "remote_control_server.py"),
    ("Images", "images_app.py"),
    ("Settings", "settings_menu.py"),
]


current_index = 0
top_index = 0
LINE_HEIGHT = 20
ITEMS_PER_SCREEN = LCD_HEIGHT // LINE_HEIGHT


def run_selected():
    script = MENU_ITEMS[current_index][1]
    device.cleanup()
    GPIO.cleanup()
    try:
        subprocess.call(["python3", script])
    finally:
        reinitialize()
        time.sleep(0.5)


print("Main menu started. Use joystick to navigate and KEY1/JOY_PRESS to select.")
try:
    while True:
        if GPIO.input(BUTTON_PINS["JOY_UP"]) == GPIO.LOW:
            prev_index = current_index
            current_index = (current_index - 1) % len(MENU_ITEMS)
            if prev_index == 0 and current_index == len(MENU_ITEMS) - 1:
                top_index = max(0, len(MENU_ITEMS) - ITEMS_PER_SCREEN)
            elif current_index < top_index:
                top_index = current_index
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["JOY_DOWN"]) == GPIO.LOW:
            prev_index = current_index
            current_index = (current_index + 1) % len(MENU_ITEMS)
            if prev_index == len(MENU_ITEMS) - 1 and current_index == 0:
                top_index = 0
            elif current_index >= top_index + ITEMS_PER_SCREEN:
                top_index = current_index - ITEMS_PER_SCREEN + 1
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW:
            run_selected()

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            for offset, (name, _) in enumerate(MENU_ITEMS[top_index:top_index + ITEMS_PER_SCREEN]):
                item_index = top_index + offset
                y = offset * LINE_HEIGHT
                if item_index == current_index:
                    draw.text((15, y), f"> {name}", fill="yellow", font=font)
                else:
                    draw.text((15, y), name, fill="white", font=font)

        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nExiting menu.")
finally:
    device.cleanup()
    GPIO.cleanup()


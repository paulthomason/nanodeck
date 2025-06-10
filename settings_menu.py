#!/usr/bin/env python3
"""Settings menu for the Waveshare 1.44"""

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

brightness = 128  # start mid-level


def brightness_menu():
    global brightness
    while True:
        if GPIO.input(BUTTON_PINS["JOY_LEFT"]) == GPIO.LOW:
            brightness = max(0, brightness - 5)
            device.contrast(brightness)
            time.sleep(0.1)
        elif GPIO.input(BUTTON_PINS["JOY_RIGHT"]) == GPIO.LOW:
            brightness = min(255, brightness + 5)
            device.contrast(brightness)
            time.sleep(0.1)
        elif GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
            return "BACK"

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((20, 50), "Brightness", fill="white", font=font)
            draw.text((20, 70), f"{brightness}", fill="yellow", font=font)
        time.sleep(0.05)


def menu_loop(menu_items):
    index = 0
    while True:
        if GPIO.input(BUTTON_PINS["JOY_UP"]) == GPIO.LOW:
            index = (index - 1) % len(menu_items)
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["JOY_DOWN"]) == GPIO.LOW:
            index = (index + 1) % len(menu_items)
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW:
            action = menu_items[index][1]
            if callable(action):
                result = action()
                if result == "BACK":
                    return
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
            return

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            for i, (name, _) in enumerate(menu_items):
                y = 40 + i * 20
                if i == index:
                    draw.text((15, y), f"> {name}", fill="yellow", font=font)
                else:
                    draw.text((15, y), name, fill="white", font=font)
        time.sleep(0.05)


def display_menu():
    menu_loop([
        ("Brightness", brightness_menu),
        ("Back", lambda: "BACK"),
    ])


def connections_menu():
    def placeholder(name):
        def inner():
            while True:
                if GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
                    return "BACK"
                with canvas(device) as draw:
                    draw.rectangle(device.bounding_box, outline="black", fill="black")
                    draw.text((20, 60), f"{name}", fill="white", font=font)
                    draw.text((20, 80), "Not implemented", fill="yellow", font=font)
                time.sleep(0.05)
        return inner

    menu_loop([
        ("WiFi", placeholder("WiFi")),
        ("Bluetooth", placeholder("Bluetooth")),
        ("Back", lambda: "BACK"),
    ])


print("Settings menu. KEY1/JOY_PRESS selects. KEY3 exits.")
try:
    menu_loop([
        ("Display", display_menu),
        ("Connections", connections_menu),
        ("Back", lambda: "BACK"),
    ])
except KeyboardInterrupt:
    pass
finally:
    device.cleanup()
    GPIO.cleanup()


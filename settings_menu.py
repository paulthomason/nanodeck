#!/usr/bin/env python3
"""Settings menu for the Waveshare 1.44"""

import time
import subprocess
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
            wait_for_release("KEY1", "JOY_PRESS", "KEY3")
            return "BACK"

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((20, 50), "Brightness", fill="white", font=font)
            draw.text((20, 70), f"{brightness}", fill="yellow", font=font)
        time.sleep(0.05)


def wait_for_release(*buttons):
    """Block until the specified buttons are released."""
    if not buttons:
        buttons = ("KEY1", "JOY_PRESS")
    while any(GPIO.input(BUTTON_PINS[b]) == GPIO.LOW for b in buttons):
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
            wait_for_release("KEY1", "JOY_PRESS")
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

def wifi_menu():
    index = 0
    networks = []

    def scan():
        nonlocal networks, index
        try:
            out = subprocess.check_output([
                "nmcli",
                "-t",
                "-f",
                "SSID",
                "device",
                "wifi",
                "list",
            ])
            networks = sorted({n.strip() for n in out.decode().splitlines() if n.strip()})
        except Exception:
            networks = []
        index = 0

    def connect(ssid: str):
        subprocess.call(["nmcli", "device", "wifi", "connect", ssid])
        time.sleep(1)

    scan()
    while True:
        if networks and GPIO.input(BUTTON_PINS["JOY_UP"]) == GPIO.LOW:
            index = (index - 1) % len(networks)
            time.sleep(0.2)
        elif networks and GPIO.input(BUTTON_PINS["JOY_DOWN"]) == GPIO.LOW:
            index = (index + 1) % len(networks)
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY2"]) == GPIO.LOW:
            scan()
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW:
            wait_for_release("KEY1", "JOY_PRESS")
            if networks:
                connect(networks[index])
            return "BACK"
        elif GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
            wait_for_release("KEY3")
            return "BACK"

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((15, 0), "WiFi", fill="white", font=font)
            if not networks:
                draw.text((15, 60), "No networks", fill="yellow", font=font)
            else:
                max_visible = 4
                start = max(0, min(index - max_visible // 2, len(networks) - max_visible))
                for offset, ssid in enumerate(networks[start : start + max_visible]):
                    y = 20 + offset * 20
                    if start + offset == index:
                        draw.text((15, y), f"> {ssid}", fill="yellow", font=font)
                    else:
                        draw.text((15, y), ssid, fill="white", font=font)
            draw.text((0, 110), "KEY2:Rescan", fill="gray", font=font)
        time.sleep(0.05)


def bluetooth_menu():
    index = 0
    devices = []

    def scan():
        nonlocal devices, index
        try:
            out = subprocess.check_output(["bluetoothctl", "devices"])
            devs = []
            for line in out.decode().splitlines():
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    devs.append((parts[1], parts[2]))
            devices = devs
        except Exception:
            devices = []
        index = 0

    def connect(mac: str):
        subprocess.call(["bluetoothctl", "connect", mac])
        time.sleep(1)

    scan()
    while True:
        if devices and GPIO.input(BUTTON_PINS["JOY_UP"]) == GPIO.LOW:
            index = (index - 1) % len(devices)
            time.sleep(0.2)
        elif devices and GPIO.input(BUTTON_PINS["JOY_DOWN"]) == GPIO.LOW:
            index = (index + 1) % len(devices)
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY2"]) == GPIO.LOW:
            scan()
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW or GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW:
            wait_for_release("KEY1", "JOY_PRESS")
            if devices:
                connect(devices[index][0])
            return "BACK"
        elif GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
            wait_for_release("KEY3")
            return "BACK"

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((15, 0), "Bluetooth", fill="white", font=font)
            if not devices:
                draw.text((15, 60), "No devices", fill="yellow", font=font)
            else:
                max_visible = 4
                start = max(0, min(index - max_visible // 2, len(devices) - max_visible))
                for offset, (_mac, name) in enumerate(devices[start : start + max_visible]):
                    y = 20 + offset * 20
                    if start + offset == index:
                        draw.text((15, y), f"> {name}", fill="yellow", font=font)
                    else:
                        draw.text((15, y), name, fill="white", font=font)
            draw.text((0, 110), "KEY2:Rescan", fill="gray", font=font)
        time.sleep(0.05)


def connections_menu():
    menu_loop([
        ("WiFi", wifi_menu),
        ("Bluetooth", bluetooth_menu),
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


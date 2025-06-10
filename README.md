# Waveshare 1.44inch LCD HAT - Raspberry Pi Integration Guide

This README provides a comprehensive guide for interacting with the Waveshare 1.44inch LCD HAT on a Raspberry Pi Zero 2 W. It covers the necessary software setup, how to drive the display using the `luma.lcd` Python library, and how to read input from the integrated buttons and joystick using `RPi.GPIO`.

## 1. Hardware Overview

* **Display:** Waveshare 1.44inch LCD HAT
    * **Controller:** ST7735S
    * **Resolution:** 128x128 pixels
    * **Interface:** 4-wire SPI
* **Host:** Raspberry Pi Zero 2 W
* **Operating System:** Raspberry Pi OS (Legacy) Lite (32-bit, Debian 11 Bullseye)

## 2. Pinout Reference

The following BCM GPIO pin numbers are used for the HAT:

* **LCD Control:**
    * `DC` (Data/Command): **GPIO 25**
    * `RST` (Reset): **GPIO 27**
    * `CS` (Chip Select, CE0): **GPIO 8** (Managed automatically by SPI driver)
    * `SCLK` (SPI Clock): **GPIO 11** (Managed automatically by SPI driver)
    * `MOSI` (SPI Data): **GPIO 10** (Managed automatically by SPI driver)
* **Buttons & Joystick:**
    * `KEY1`: **GPIO 21**
    * `KEY2`: **GPIO 20**
    * `KEY3`: **GPIO 16**
    * `Joystick UP`: **GPIO 6**
    * `Joystick DOWN`: **GPIO 19**
    * `Joystick LEFT`: **GPIO 5**
    * `Joystick RIGHT`: **GPIO 26**
    * `Joystick PRESS`: **GPIO 13**

## 3. Software Setup (Fresh OS Install)

Follow these steps on a fresh Raspberry Pi OS (Legacy) Lite (32-bit) install to prepare your environment.

1.  **System Update & Core Python Tools:**
    ```bash
    sudo apt update
    sudo apt upgrade -y
    sudo apt install python3-full -y
    ```
2.  **Pillow (PIL) System Dependencies:** (Required for `luma.lcd` to draw images and text)
    ```bash
    sudo apt install -y build-essential python3-dev \
        libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
        libopenjp2-7 libtiff5 libwebp-dev tcl-dev tk-dev
    ```
3.  **Standard `RPi.GPIO` Library:** (For button/joystick input on Bullseye)
    ```bash
    sudo apt install python3-rpi.gpio -y
    ```
4.  **Grant User GPIO & SPI Permissions:** (Replace `owner` with your actual username)
    ```bash
    sudo usermod -a -G spi,gpio owner
    ```
5.  **Reboot Raspberry Pi:** (Essential for group changes to take effect)
    ```bash
    sudo reboot
    ```
6.  **Create & Activate Python Virtual Environment:** (Do this in your project directory, e.g., `~/my_project/`)
    ```bash
    cd ~
    python3 -m venv my_project_env # Create a virtual environment
    source ~/my_project_env/bin/activate # Activate it (your prompt changes)
    ```
7.  **Install Python Libraries:** (Inside the active virtual environment, **no `sudo`**)
    ```bash
    pip install -r requirements.txt
    ```
    The `psutil` package is optional and used for system monitoring examples.

## 4. Writing to the Screen (`luma.lcd`)

The `luma.lcd` library provides a high-level API to draw text, shapes, and images on the ST7735S display.

### Basic Setup:

```python
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont, ImageDraw, Image

# Display pin configuration
RST_PIN = 27  # GPIO 27
DC_PIN = 25   # GPIO 25
# CS (GPIO 8), SCLK (GPIO 11), MOSI (GPIO 10) are handled by the SPI interface

# SPI communication setup (port=0, device=0 corresponds to SPI0 CE0/GPIO 8)
serial_interface = spi(port=0, device=0, cs_high=False,
                       gpio_DC=DC_PIN, gpio_RST=RST_PIN,
                       speed_hz=16000000) # 16MHz is a good speed for ST7735S

# LCD device initialization
device = st7735(serial_interface, width=128, height=128, h_offset=2, v_offset=1)
# h_offset/v_offset may need minor tuning for perfect alignment on 128x128 physical screens
```

## 5. Settings Menu

From the main menu you can open a simple settings application. The following options are available:

* **Display → Brightness** – adjust the LCD brightness using the joystick left/right.
* **Connections → WiFi** – scan for nearby networks and attempt to connect. Press `KEY2` to rescan.
* **Connections → Bluetooth** – list Bluetooth devices and connect to one. Press `KEY2` to rescan.
* **IRC Chat** – open a basic IRC client to read and send messages. Chat output
  is displayed directly on the LCD.
  * The client now always connects to `192.168.0.81` on port `6667` and joins
    the `#pet` channel using the nickname `birdie`.
* **Remote Web Server** – start a simple HTTP server for controlling the device remotely.


## License

This project is licensed under the [MIT License](LICENSE).


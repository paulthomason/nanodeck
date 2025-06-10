#!/usr/bin/env python3

import time
from datetime import datetime
import RPi.GPIO as GPIO # This is for the buttons and joystick
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont, ImageDraw

# --- Display Configuration (from previous script, corrected pins) ---
# !!! IMPORTANT: VERIFY THESE GPIO PIN NUMBERS AGAINST YOUR HAT'S DOCUMENTATION !!!
RST_PIN = 27  # GPIO pin connected to the RST (Reset) line 
DC_PIN = 25   # GPIO pin connected to the DC (Data/Command) line 

LCD_WIDTH = 128
LCD_HEIGHT = 128

serial = spi(port=0, device=0, cs_high=False,
             gpio_DC=DC_PIN, gpio_RST=RST_PIN,
             speed_hz=16000000)

device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1)

try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", 10) # Smaller font for more text
except IOError:
    font = ImageFont.load_default()

# --- GPIO Configuration for Buttons and Joystick ---
# Using BCM (Broadcom) GPIO numbering
GPIO.setmode(GPIO.BCM)

# Define button/joystick pins based on Waveshare Wiki 
BUTTON_PINS = {
    "KEY1": 21,
    "KEY2": 20,
    "KEY3": 16,
    "JOY_UP": 6,
    "JOY_DOWN": 19,
    "JOY_LEFT": 5,
    "JOY_RIGHT": 26,
    "JOY_PRESS": 13
}

# Set up each button pin as an input with a pull-up resistor
# Buttons typically connect to ground when pressed, so PUD_UP makes them HIGH when not pressed.
for pin_name, pin_num in BUTTON_PINS.items():
    GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- Event Detection for Button Presses (for console output) ---
# This will print a message to the terminal whenever a button state changes
# `GPIO.FALLING` means it triggers when the button is pressed (goes from HIGH to LOW)
# `bouncetime` helps prevent multiple detections from a single press.
def button_callback(channel):
    pin_name = next((name for name, num in BUTTON_PINS.items() if num == channel), f"Pin {channel}")
    if GPIO.input(channel) == GPIO.LOW: # Button is pressed (pulled low)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {pin_name} PRESSED!")
    else: # Button is released (goes back high)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {pin_name} Released.")

# Add event detection to all button pins
for pin_name, pin_num in BUTTON_PINS.items():
    GPIO.add_event_detect(pin_num, GPIO.BOTH, callback=button_callback, bouncetime=200)

print("Screen and input test started. Press Ctrl+C to exit.")
print("Press buttons/joystick, and observe console output & LCD display.")

# --- Main Display and Input Polling Loop ---
try:
    while True:
        with canvas(device) as draw:
            # Clear the screen
            draw.rectangle(device.bounding_box, outline="black", fill="black")

            # Display Time and Date
            now = datetime.now()
            draw.text((5, 0), now.strftime("%H:%M:%S"), fill="white", font=font)
            draw.text((5, 10), now.strftime("%Y-%m-%d"), fill="gray", font=font)

            # Display Button States
            y_offset = 25
            for pin_name, pin_num in BUTTON_PINS.items():
                state = "OFF"
                color = "red"
                if GPIO.input(pin_num) == GPIO.LOW: # Button is pressed
                    state = "ON"
                    color = "green"
                draw.text((5, y_offset), f"{pin_name}: {state}", fill=color, font=font)
                y_offset += 10 # Move to the next line

            # Simple animated rectangle (from previous test)
            rect_x = int(5 + (time.time() * 10) % (LCD_WIDTH - 25))
            draw.rectangle((rect_x, 100, rect_x + 20, 115), outline="blue", fill="yellow")


        time.sleep(0.05) # Update faster to feel more responsive for input (~20 FPS)

except KeyboardInterrupt:
    print("\nExiting screen and input test.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
finally:
    print("Cleaning up display and GPIO resources...")
    device.cleanup() # Cleans up luma.lcd resources
    GPIO.cleanup()   # Cleans up RPi.GPIO resources
    print("Cleanup complete.")

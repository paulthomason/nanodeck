#!/usr/bin/env python3

import time
from datetime import datetime
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont, ImageDraw

# --- Configuration for your Waveshare 1.44inch LCD HAT ---
# !!! CORRECTED GPIO PIN NUMBERS BASED ON WAVESHARE WIKI !!! 
RST_PIN = 27  # GPIO pin connected to the RST (Reset) line 
DC_PIN = 25   # GPIO pin connected to the DC (Data/Command) line 
# CS_PIN (GPIO 8 / CE0) is handled automatically by luma.lcd's spi interface (device=0) 

# Display dimensions
LCD_WIDTH = 128  # Resolution of the LCD 
LCD_HEIGHT = 128 # Resolution of the LCD 

# SPI Configuration
# port=0, device=0 means SPI0 CE0. This is standard and matches CS=P8/CE0. 
# cs_high=False: Chip Select is active LOW (standard for most SPI devices). 
# speed_hz: Max SPI speed (ST7735 can often handle 16MHz or higher).
serial = spi(port=0, device=0, cs_high=False,
             gpio_DC=DC_PIN, gpio_RST=RST_PIN,
             speed_hz=16000000)

# Initialize the ST7735S display device
# h_offset and v_offset are common for ST7735S on 128x128 displays
# and might need minor tuning if your display area is slightly off-center. 
device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1)

# --- Button setup ---
GPIO.setmode(GPIO.BCM)
KEY3_PIN = 16
GPIO.setup(KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Load a default font (or specify a path to a .ttf font file if you have one)
try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", 14)
except IOError:
    # Fallback to default PIL font if DejaVuSansMono.ttf is not found
    font = ImageFont.load_default()

print("Screen test started. Press Ctrl+C to exit.")

try:
    while True:
        if GPIO.input(KEY3_PIN) == GPIO.LOW:
            break
        # Create a new drawing canvas
        with canvas(device) as draw:
            # Clear the screen (fill with black)
            draw.rectangle(device.bounding_box, outline="black", fill="black")

            # Get current time and date
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_date = now.strftime("%Y-%m-%d")

            # Draw text strings on the display
            draw.text((5, 5), "Waveshare LCD HAT", fill="white", font=font)
            draw.text((5, 25), f"Time: {current_time}", fill="cyan", font=font)
            draw.text((5, 45), f"Date: {current_date}", fill="lime", font=font)
            draw.text((5, 65), "Working!", fill="yellow", font=font)

            # Draw a simple animated rectangle
            # Its horizontal position shifts based on the current time (seconds), creating movement
            rect_x = int(5 + (time.time() * 20) % (LCD_WIDTH - 20))
            draw.rectangle((rect_x, 90, rect_x + 15, 105), outline="red", fill="blue")

        # Pause for a short period before updating the display again
        time.sleep(0.1) # Updates the display approximately 10 times per second

except KeyboardInterrupt:
    # Handles a graceful exit when Ctrl+C is pressed in the terminal
    print("\nExiting screen test.")
except Exception as e:
    # Catches any other unexpected errors during execution
    print(f"\nAn unexpected error occurred: {e}")
finally:
    # Ensures cleanup operations are performed whether the script exits normally or due to an error
    print("Cleaning up display...")
    device.cleanup() # Cleans up the luma.lcd device resources
    GPIO.cleanup()
    print("Cleanup complete.")

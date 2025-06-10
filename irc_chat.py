#!/usr/bin/env python3
"""Simple console IRC client for #pet on 192.168.0.81."""

import socket
import threading
import textwrap
import time

import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont

# Connection details are now fixed so that the client always connects to
# 192.168.0.81 on port 6667 using nickname "birdie" in channel "#pet".
SERVER = "192.168.0.81"
PORT = 6667
CHANNEL = "#pet"
NICK = "birdie"

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
    font = ImageFont.truetype("DejaVuSansMono.ttf", 10)
except IOError:
    font = ImageFont.load_default()

GPIO.setmode(GPIO.BCM)
EXIT_PIN = 16  # KEY3 on the Waveshare HAT
GPIO.setup(EXIT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

messages: list[str] = []


def draw_messages() -> None:
    """Render the last messages to the LCD."""
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        start = max(0, len(messages) - 10)
        for i, msg in enumerate(messages[start:]):
            draw.text((0, i * 12), msg, fill="white", font=font)


def add_message(text: str) -> None:
    """Add text to the message buffer and redraw."""
    for line in textwrap.wrap(text, width=21):
        messages.append(line)
    if len(messages) > 30:
        del messages[:-30]
    draw_messages()


def get_text_input(prompt: str = "") -> str:
    """Return text entered by the user."""
    try:
        return input(prompt)
    except EOFError:
        return ""


def _send(sock: socket.socket, msg: str) -> None:
    sock.sendall(msg.encode("utf-8"))


def _handle_server(sock: socket.socket) -> None:
    buffer = ""
    while True:
        data = sock.recv(4096).decode("utf-8", "ignore")
        if not data:
            break
        buffer += data
        while "\r\n" in buffer:
            line, buffer = buffer.split("\r\n", 1)
            if line.startswith("PING"):
                _send(sock, f"PONG {line.split()[1]}\r\n")
            else:
                if " PRIVMSG " in line and " :" in line:
                    prefix, rest = line.split(" PRIVMSG ", 1)
                    target, text = rest.split(" :", 1)
                    if target == CHANNEL:
                        nick = prefix.split("!")[0][1:] if line.startswith(":") else prefix
                        add_message(f"{nick}: {text}")
                else:
                    add_message(line)


def main() -> None:
    with socket.socket() as sock:
        sock.connect((SERVER, PORT))
        _send(sock, f"NICK {NICK}\r\n")
        _send(sock, f"USER {NICK} 0 * :{NICK}\r\n")
        _send(sock, f"JOIN {CHANNEL}\r\n")

        thread = threading.Thread(target=_handle_server, args=(sock,), daemon=True)
        thread.start()

        try:
            while True:
                if GPIO.input(EXIT_PIN) == GPIO.LOW:
                    break
                message = get_text_input("> ")
                if not message:
                    continue
                if message.lower() == "/quit":
                    break
                _send(sock, f"PRIVMSG {CHANNEL} :{message}\r\n")
                add_message(f"{NICK}: {message}")
        finally:
            _send(sock, "QUIT :Bye\r\n")
            device.cleanup()
            GPIO.cleanup()


if __name__ == "__main__":
    main()

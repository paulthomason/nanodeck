"""Simple web server for remote control of the Raspberry Pi."""

import html
import http.server
import queue
import socket
import threading
import time
import urllib.parse

import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont

# Global variables for communication with the main application
from typing import Optional

remote_input_queue: queue.Queue[str] = queue.Queue()
remote_image_request: Optional[str] = None

# List of images available for viewing
AVAILABLE_IMAGES: list[str] = [
    "image1.png",
    "sunset.jpg",
    "mountain.png",
]

_server_thread = None
_server = None

# --- Display setup ---
RST_PIN = 27
DC_PIN = 25
LCD_WIDTH = 128
LCD_HEIGHT = 128

serial = spi(
    port=0,
    device=0,
    cs_high=False,
    gpio_DC=DC_PIN,
    gpio_RST=RST_PIN,
    speed_hz=16000000,
)

device = st7735(
    serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1
)

try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", 12)
except IOError:
    font = ImageFont.load_default()

# --- Button setup ---
GPIO.setmode(GPIO.BCM)
BUTTON_PINS = {
    "KEY1": 21,
    "KEY3": 16,
    "JOY_PRESS": 13,
}
for pin in BUTTON_PINS.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


class RemoteHandler(http.server.BaseHTTPRequestHandler):
    """Handle HTTP requests for the remote control interface."""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            ip_addr = get_pi_ip_address()
            html_doc = self._build_index_page(ip_addr)
            self.wfile.write(html_doc.encode("utf-8"))
        elif parsed.path == "/input":
            params = urllib.parse.parse_qs(parsed.query)
            button_id = params.get("button_id", [None])[0]
            if button_id:
                remote_input_queue.put(button_id)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        elif parsed.path == "/view_image":
            params = urllib.parse.parse_qs(parsed.query)
            image_name = params.get("image_name", [None])[0]
            if image_name:
                global remote_image_request
                remote_image_request = image_name
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_error(404)

    def _build_index_page(self, ip_addr: str) -> str:
        """Return the HTML for the main control page."""
        joystick_buttons = [
            ("JOY_UP", "UP"),
            ("JOY_DOWN", "DOWN"),
            ("JOY_LEFT", "LEFT"),
            ("JOY_RIGHT", "RIGHT"),
            ("JOY_PRESS", "PRESS"),
        ]
        hat_buttons = ["KEY1", "KEY2", "KEY3"]

        btn = "".join(
            (
                f'<a href="/input?button_id={html.escape(b)}">'
                f'<button class="joystick">{html.escape(label)}</button></a>'
            )
            for b, label in joystick_buttons
        )
        hat_btn = "".join(
            (
                f'<a href="/input?button_id={html.escape(b)}">'
                f'<button class="key">{html.escape(b)}</button></a>'
            )
            for b in hat_buttons
        )
        images = "".join(
            (
                f'<li><a href="/view_image?image_name={html.escape(img)}">'
                f'{html.escape(img)}</a></li>'
            )
            for img in AVAILABLE_IMAGES
        )
        style = (
            "<style>"
            "body{font-family:Arial,sans-serif;text-align:center;}"
            "button{padding:15px 20px;font-size:18px;margin:5px;}"
            ".joystick{background:#4CAF50;color:white;}"
            ".key{background:#2196F3;color:white;}"
            "ul{list-style:none;padding:0;}"
            "</style>"
        )
        html_doc = (
            "<html><head>" + style + "</head><body>"
            "<h1>Pi Remote Control</h1>"
            f"<p>IP Address: {html.escape(ip_addr)}</p>"
            f"<div>{btn}</div><div>{hat_btn}</div>"
            "<h2>Images</h2><ul>" + images + "</ul>"
            "</body></html>"
        )
        return html_doc


def get_pi_ip_address() -> str:
    """Return the Pi's local IP address or 127.0.0.1 if unknown."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the remote control HTTP server."""
    global _server_thread, _server
    if _server_thread and _server_thread.is_alive():
        return
    _server = http.server.ThreadingHTTPServer((host, port), RemoteHandler)
    _server_thread = threading.Thread(
        target=_server.serve_forever, daemon=True
    )
    _server_thread.start()


def stop_server() -> None:
    """Stop the running HTTP server if it is active."""
    global _server_thread, _server
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None
    if _server_thread:
        _server_thread.join(timeout=1)
        _server_thread = None


def remote_menu() -> None:
    """Display a simple interface to toggle the web server."""
    running = _server_thread is not None and _server_thread.is_alive()
    ip_addr = get_pi_ip_address()
    while True:
        if (
            GPIO.input(BUTTON_PINS["KEY1"]) == GPIO.LOW
            or GPIO.input(BUTTON_PINS["JOY_PRESS"]) == GPIO.LOW
        ):
            if running:
                stop_server()
                running = False
            else:
                start_server()
                running = True
                ip_addr = get_pi_ip_address()
            time.sleep(0.2)
        elif GPIO.input(BUTTON_PINS["KEY3"]) == GPIO.LOW:
            break

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((10, 30), "Remote Server", fill="white", font=font)
            status = "ON" if running else "OFF"
            color = "green" if running else "red"
            draw.text((10, 60), f"Status: {status}", fill=color, font=font)
            if running:
                draw.text(
                    (10, 80), f"{ip_addr}:8000", fill="yellow", font=font
                )
        time.sleep(0.05)


if __name__ == "__main__":
    try:
        remote_menu()
    except KeyboardInterrupt:
        pass
    finally:
        device.cleanup()
        GPIO.cleanup()

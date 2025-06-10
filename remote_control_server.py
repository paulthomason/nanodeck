"""Simple web server for remote control of the Raspberry Pi."""

import html
import http.server
import queue
import socket
import threading
import time
import urllib.parse

# Global variables for communication with the main application
remote_input_queue: queue.Queue[str] = queue.Queue()
remote_image_request: str | None = None

# List of images available for viewing
AVAILABLE_IMAGES: list[str] = [
    "image1.png",
    "sunset.jpg",
    "mountain.png",
]

_server_thread = None


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
            f'<a href="/input?button_id={html.escape(b)}"><button class="joystick">{html.escape(label)}</button></a>'
            for b, label in joystick_buttons
        )
        hat_btn = "".join(
            f'<a href="/input?button_id={html.escape(b)}"><button class="key">{html.escape(b)}</button></a>'
            for b in hat_buttons
        )
        images = "".join(
            f'<li><a href="/view_image?image_name={html.escape(img)}">{html.escape(img)}</a></li>'
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
            f"<h1>Pi Remote Control</h1><p>IP Address: {html.escape(ip_addr)}</p>"
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
    global _server_thread
    if _server_thread:
        return
    server = http.server.ThreadingHTTPServer((host, port), RemoteHandler)
    _server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    _server_thread.start()


def draw_remote(screen, FONT) -> None:
    """Placeholder for drawing remote status on the LCD."""
    pass


if __name__ == "__main__":
    start_server()
    ip = get_pi_ip_address()
    print(f"Remote server running on http://{ip}:8000/ (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

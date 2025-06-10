#!/usr/bin/env python3
"""IRC chat viewer using luma.lcd and RPi.GPIO."""

import time
import socket
import threading
import queue
import logging

import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont

# --- Display configuration ---
RST_PIN = 27
DC_PIN = 25
LCD_WIDTH = 128
LCD_HEIGHT = 128

serial = spi(port=0, device=0, cs_high=False,
             gpio_DC=DC_PIN, gpio_RST=RST_PIN,
             speed_hz=16000000)

device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT,
                h_offset=2, v_offset=1)

# --- Font setup ---
try:
    CHAT_FONT = ImageFont.truetype("DejaVuSansMono.ttf", 14)
except IOError:
    CHAT_FONT = ImageFont.load_default()

LINE_HEIGHT = CHAT_FONT.getbbox("A")[3] - CHAT_FONT.getbbox("A")[1] + 2

# --- Input configuration ---
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

# --- Typing state ---
keyboard_chars = list("abcdefghijklmnopqrstuvwxyz0123456789.,!? ")
VISIBLE = 10
cursor = 0
scroll = 0
typed_text = ""
shift = False
chat_scroll = 0

send_queue: queue.Queue[str] = queue.Queue()
NICK = "birdie"
nick_colors: dict[str, tuple[int, int, int]] = {}
PALETTE = [
    (255, 96, 96),
    (96, 255, 96),
    (96, 96, 255),
    (255, 255, 96),
    (255, 96, 255),
    (96, 255, 255),
    (255, 160, 96),
    (160, 96, 255),
]
MAX_VISIBLE = 5
chat_lines = []
_init = False
_thread = None
logger = logging.getLogger(__name__)


def get_nick_color(nick: str) -> tuple[int, int, int]:
    if nick == NICK:
        return (96, 255, 255)
    if nick not in nick_colors:
        nick_colors[nick] = PALETTE[len(nick_colors) % len(PALETTE)]
    return nick_colors[nick]


def wrap_text(text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.getlength(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        while word and font.getlength(word) > width:
            end = len(word)
            while end > 0 and font.getlength(word[:end]) > width:
                end -= 1
            if end == 0:
                break
            lines.append(word[:end])
            word = word[end:]
        current = word
    if current:
        lines.append(current)
    return lines


def _irc_thread(server: str, port: int, channel: str, nick: str) -> None:
    def send(msg: str) -> None:
        sock.sendall(msg.encode("utf-8"))

    try:
        sock = socket.socket()
        sock.connect((server, port))
        logger.debug(f"Connected to {server}:{port}, joining {channel} as {nick}")
        send(f"NICK {nick}\r\n")
        send(f"USER {nick} 0 * :{nick}\r\n")
        send(f"JOIN {channel}\r\n")

        buffer = ""
        sock.settimeout(0.1)
        while True:
            try:
                while True:
                    out = send_queue.get_nowait()
                    send(f"PRIVMSG {channel} :{out}\r\n")
            except queue.Empty:
                pass

            try:
                data = sock.recv(4096).decode("utf-8", "ignore")
                if not data:
                    break
            except socket.timeout:
                data = ""
            buffer += data
            while "\r\n" in buffer:
                line, buffer = buffer.split("\r\n", 1)
                if line.startswith("PING"):
                    send(f"PONG {line.split()[1]}\r\n")
                    continue
                parts = line.split(" ", 3)
                if len(parts) >= 4 and parts[1] == "PRIVMSG":
                    user = parts[0].split("!")[0][1:]
                    msg = parts[3][1:]
                    chat_lines.append({"user": user, "msg": msg})
                    if len(chat_lines) > 100:
                        chat_lines.pop(0)
    except Exception as exc:
        error_msg = f"IRC connection error: {exc}"
        print(error_msg)
        logger.exception(error_msg)
        chat_lines.append({"user": "error", "msg": str(exc)})


def init_chat() -> None:
    global _init, _thread
    if _init:
        return
    server = "192.168.0.81"  # <-- Replace with your IRC server
    port = 6667
    channel = "#pet"        # <-- Replace with your desired channel
    nick = NICK
    logger.debug(f"Starting IRC thread for {server}:{port} {channel} as {nick}")
    _thread = threading.Thread(target=_irc_thread, args=(server, port, channel, nick), daemon=True)
    _thread.start()
    _init = True


def send_chat_message(message: str) -> None:
    if message:
        send_queue.put(message)
        chat_lines.append({"user": NICK, "msg": message})
        if len(chat_lines) > 100:
            chat_lines.pop(0)


def draw_chat(draw):
    font = CHAT_FONT
    draw.rectangle(device.bounding_box, outline="black", fill="black")
    max_width = device.width - 12
    rendered_lines = []
    for chat in chat_lines:
        prefix = f"{chat['user']}> "
        prefix_width = font.getlength(prefix)
        parts = wrap_text(chat["msg"], font, max_width - prefix_width)
        if not parts:
            parts = [""]
        prefix_color = get_nick_color(chat["user"])
        text_color = (96, 255, 255) if chat["user"] == NICK else (255, 255, 255)
        for idx, part in enumerate(parts):
            if idx == 0:
                rendered_lines.append((prefix, part, prefix_color, text_color, 6))
            else:
                rendered_lines.append(("", part, prefix_color, text_color, 6))

    start = max(0, len(rendered_lines) - MAX_VISIBLE - chat_scroll)
    end = max(0, len(rendered_lines) - chat_scroll)
    visible = rendered_lines[start:end]

    for i, (pref, text, pref_c, txt_c, x) in enumerate(visible):
        y = 15 + i * LINE_HEIGHT
        if pref:
            draw.text((x, y), pref, fill=pref_c, font=font)
            draw.text((x + font.getlength(pref), y), text, fill=txt_c, font=font)
        else:
            draw.text((x, y), text, fill=txt_c, font=font)

    input_display = typed_text[-16:]
    draw.text((6, 108), f"> {input_display}", fill="white", font=font)

    start_k = scroll
    end_k = scroll + VISIBLE
    for i, ch in enumerate(keyboard_chars[start_k:end_k]):
        idx = start_k + i
        color = "yellow" if idx == cursor else "white"
        disp_ch = ch.upper() if shift else ch
        x = 6 + i * 12
        draw.text((x, 88), disp_ch, fill=color, font=font)

    draw.text((2, 2), "ARROWS Type TAB=Shift RET=Send ESC=Back", fill="white", font=font)


prev_states = {name: GPIO.input(pin) for name, pin in BUTTON_PINS.items()}
last_press = {name: 0.0 for name in BUTTON_PINS}
DEBOUNCE = 0.2


def handle_button(name: str) -> None:
    global cursor, scroll, typed_text, shift
    if name == "JOY_LEFT":
        cursor = (cursor - 1) % len(keyboard_chars)
    elif name == "JOY_RIGHT":
        cursor = (cursor + 1) % len(keyboard_chars)
    elif name == "JOY_UP":
        ch = keyboard_chars[cursor]
        if shift:
            ch = ch.upper()
            shift = False
        typed_text += ch
        if len(typed_text) > 200:
            typed_text = typed_text[-200:]
    elif name == "JOY_DOWN":
        typed_text = typed_text[:-1]
    elif name in ("KEY1", "JOY_PRESS"):
        send_chat_message(typed_text)
        typed_text = ""
    elif name == "KEY2":
        shift = not shift
    elif name == "KEY3":
        typed_text = ""

    if cursor < scroll:
        scroll = cursor
    elif cursor >= scroll + VISIBLE:
        scroll = cursor - VISIBLE + 1


def poll_inputs() -> None:
    now = time.time()
    for name, pin in BUTTON_PINS.items():
        state = GPIO.input(pin)
        if state == GPIO.LOW and prev_states[name] == GPIO.HIGH:
            if now - last_press[name] > DEBOUNCE:
                handle_button(name)
                last_press[name] = now
        prev_states[name] = state


def main():
    logging.basicConfig(level=logging.INFO)
    init_chat()
    try:
        while True:
            poll_inputs()
            with canvas(device) as draw:
                draw_chat(draw)
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        device.cleanup()
        GPIO.cleanup()


if __name__ == "__main__":
    main()

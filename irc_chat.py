#!/usr/bin/env python3
"""Simple console IRC client for #pet on 192.168.0.81."""

import socket
import threading

# Connection details are now fixed so that the client always connects to
# 192.168.0.81 on port 6667 using nickname "birdie" in channel "#pet".
SERVER = "192.168.0.81"
PORT = 6667
CHANNEL = "#pet"
NICK = "birdie"


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
                print(line)


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
                message = get_text_input("> ")
                if not message:
                    continue
                if message.lower() == "/quit":
                    break
                _send(sock, f"PRIVMSG {CHANNEL} :{message}\r\n")
        finally:
            _send(sock, "QUIT :Bye\r\n")


if __name__ == "__main__":
    main()

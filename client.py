"""
Secure Socket Chat — Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CLI chat client with AES-256 end-to-end encryption (Fernet).
Connects to the chat server, encrypts outgoing messages and
decrypts incoming traffic.

Usage:
    python client.py [--host HOST] [--port PORT]
"""

import socket
import threading
import argparse
import sys
from cryptography.fernet import Fernet, InvalidToken

# ──────────────────────────────────────────────
#  Defaults
# ──────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55555
BUFFER_SIZE = 4096
NICK_REQUEST = "NICK"

# ──────────────────────────────────────────────
#  Encryption
# ──────────────────────────────────────────────
# NOTE: In production this key should be exchanged via Diffie-Hellman
# or another key-agreement protocol. A static key is used here for
# demonstration purposes only.
SHARED_KEY = b"wXz-2p4fG8yN1qZ9_J7kL3vM6tB0hR5dS8oA4eC1uI="
cipher = Fernet(SHARED_KEY)


class ChatClient:
    """Encrypted TCP chat client."""

    def __init__(self, host: str, port: int, nickname: str) -> None:
        self.host = host
        self.port = port
        self.nickname = nickname
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False

    # ── connection ───────────────────────────
    def connect(self) -> None:
        """Establish a TCP connection to the chat server."""
        try:
            self.sock.connect((self.host, self.port))
        except ConnectionRefusedError:
            print("[!] Server unreachable. Make sure server.py is running.")
            sys.exit(1)

        self.running = True

    # ── receive loop ─────────────────────────
    def _receive_loop(self) -> None:
        """Continuously read from the socket, decrypt, and display."""
        while self.running:
            try:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break

                text = data.decode("utf-8")

                # Server asks for nickname during handshake
                if text == NICK_REQUEST:
                    self.sock.send(self.nickname.encode("utf-8"))
                    continue

                # Try decryption — falls back to plaintext for server
                # announcements (join/leave notices etc.)
                try:
                    decrypted = cipher.decrypt(data).decode("utf-8")
                    print(decrypted)
                except InvalidToken:
                    print(text)

            except OSError:
                break

        self._disconnect()

    # ── send loop ────────────────────────────
    def _send_loop(self) -> None:
        """Read user input, encrypt, and transmit."""
        while self.running:
            try:
                text = input()
            except (EOFError, KeyboardInterrupt):
                break

            if not text:
                continue

            payload = f"{self.nickname}: {text}"
            encrypted = cipher.encrypt(payload.encode("utf-8"))

            try:
                self.sock.send(encrypted)
            except OSError:
                break

        self._disconnect()

    # ── lifecycle ────────────────────────────
    def _disconnect(self) -> None:
        """Close the socket and flip the running flag."""
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

    def run(self) -> None:
        """Start the receive and send threads."""
        recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        recv_thread.start()

        # send loop runs on the main thread so Ctrl+C works
        self._send_loop()


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Secure Socket Chat — Client")
    parser.add_argument("--host", default=DEFAULT_HOST, help="server address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="server port")
    args = parser.parse_args()

    nickname = input("Nickname: ").strip()
    if not nickname:
        print("[!] Nickname cannot be empty.")
        sys.exit(1)

    client = ChatClient(host=args.host, port=args.port, nickname=nickname)
    client.connect()

    print(f"[*] Connecting to {args.host}:{args.port} …")
    client.run()


if __name__ == "__main__":
    main()
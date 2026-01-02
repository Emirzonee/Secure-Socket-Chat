"""
Secure Socket Chat — Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Multi-client TCP chat server with threading support.
Handles client connections, nickname registration, and
encrypted message broadcasting.

Usage:
    python server.py [--host HOST] [--port PORT]
"""

import socket
import threading
import argparse
import logging
import signal
import sys
from datetime import datetime

# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Defaults
# ──────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55555
BUFFER_SIZE = 4096
NICK_REQUEST = "NICK"


class ChatServer:
    """TCP chat server that relays encrypted messages between clients."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.clients: list[socket.socket] = []
        self.nicknames: list[str] = []
        self.lock = threading.Lock()          # thread-safe client list ops
        self.running = False

    # ── broadcast ────────────────────────────
    def broadcast(self, data: bytes, exclude: socket.socket | None = None) -> None:
        """Send *data* to every connected client, optionally skipping one."""
        with self.lock:
            for client in list(self.clients):
                if client is exclude:
                    continue
                try:
                    client.send(data)
                except OSError:
                    self._remove_client(client)

    # ── client removal ───────────────────────
    def _remove_client(self, client: socket.socket) -> None:
        """Remove a client from the active lists and notify others."""
        if client not in self.clients:
            return

        idx = self.clients.index(client)
        nickname = self.nicknames[idx]

        self.clients.pop(idx)
        self.nicknames.pop(idx)
        client.close()

        logger.info("Disconnected: %s", nickname)
        self.broadcast(f"{nickname} left the chat.".encode("utf-8"))

    # ── per-client handler ───────────────────
    def _handle_client(self, client: socket.socket) -> None:
        """Listen loop for a single client; runs in its own thread."""
        while self.running:
            try:
                data = client.recv(BUFFER_SIZE)
                if not data:
                    break
                self.broadcast(data)
            except OSError:
                break

        with self.lock:
            self._remove_client(client)

    # ── accept loop ──────────────────────────
    def _accept_connections(self) -> None:
        """Main loop — accept new connections and spin up handler threads."""
        while self.running:
            try:
                client, address = self.server_socket.accept()
            except OSError:
                break

            logger.info("Connection from %s:%d", *address)

            # Nickname handshake
            try:
                client.send(NICK_REQUEST.encode("utf-8"))
                nickname = client.recv(BUFFER_SIZE).decode("utf-8").strip()
                if not nickname:
                    raise ValueError("empty nickname")
            except (OSError, ValueError):
                client.close()
                continue

            with self.lock:
                self.clients.append(client)
                self.nicknames.append(nickname)

            logger.info("Registered: %s", nickname)

            self.broadcast(f"{nickname} joined the chat.".encode("utf-8"), exclude=client)
            client.send("Connected to the server.".encode("utf-8"))

            thread = threading.Thread(
                target=self._handle_client,
                args=(client,),
                daemon=True,
            )
            thread.start()

    # ── start / stop ─────────────────────────
    def start(self) -> None:
        """Bind, listen, and begin accepting clients."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.running = True

        logger.info("Server listening on %s:%d", self.host, self.port)

        self._accept_connections()

    def shutdown(self) -> None:
        """Gracefully close all connections and the server socket."""
        self.running = False
        logger.info("Shutting down…")

        with self.lock:
            for client in list(self.clients):
                try:
                    client.close()
                except OSError:
                    pass
            self.clients.clear()
            self.nicknames.clear()

        self.server_socket.close()
        logger.info("Server stopped.")


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Secure Socket Chat — Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port")
    args = parser.parse_args()

    server = ChatServer(host=args.host, port=args.port)

    # Handle Ctrl+C gracefully
    def _signal_handler(sig, frame):
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)

    server.start()


if __name__ == "__main__":
    main()
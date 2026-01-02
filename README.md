# Secure Socket Chat

A multi-client terminal chat application built with Python sockets and threading. Messages are encrypted end-to-end using AES-256 (Fernet) so that even if traffic is intercepted, the content stays unreadable.

## Architecture

```
┌──────────┐         TCP          ┌──────────────┐         TCP          ┌──────────┐
│  Client A │ ◄──── encrypted ───► │    Server    │ ◄──── encrypted ───► │  Client B │
│  (Fernet) │       messages       │  (broadcast) │       messages       │  (Fernet) │
└──────────┘                      └──────────────┘                      └──────────┘
```

The server acts as a relay — it accepts connections, manages nicknames, and broadcasts raw (still-encrypted) bytes to all connected clients. Decryption happens only on the client side, so the server never sees plaintext messages.

## Features

- **AES-256 encryption** — all chat messages are encrypted with Fernet (symmetric) before leaving the client
- **Multi-client support** — server handles concurrent connections via threading
- **Thread-safe broadcasting** — client list operations are protected with a `threading.Lock`
- **Graceful shutdown** — `Ctrl+C` cleanly disconnects clients and stops the server
- **CLI arguments** — configurable host/port via `--host` and `--port` flags

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/Emirzonee/Secure-Socket-Chat.git
cd Secure-Socket-Chat
pip install -r requirements.txt
```

### Running

**1. Start the server:**

```bash
python server.py
```

**2. In separate terminals, start one or more clients:**

```bash
python client.py
```

Custom host and port:

```bash
python server.py --host 0.0.0.0 --port 8080
python client.py --host 192.168.1.10 --port 8080
```

## How It Works

1. The server starts listening on the configured address.
2. When a client connects, the server sends `NICK` — the client responds with its nickname.
3. The server announces the new user to all other clients (plaintext announcement).
4. Each message the client sends is encrypted with the shared Fernet key before transmission.
5. The server receives the encrypted bytes and broadcasts them as-is to every other client.
6. Receiving clients decrypt the bytes back to plaintext and display the message.

## Security Notes

The current implementation uses a **hardcoded symmetric key** shared across all clients. This is intentional for demonstration purposes. In a production setting you would want:

- A key-exchange protocol like **Diffie-Hellman** or **ECDH** to establish per-session keys
- **TLS/SSL** wrapping on the TCP socket (`ssl.wrap_socket`)
- Per-message authentication (Fernet already includes HMAC, but session binding would add another layer)

## Project Structure

```
Secure-Socket-Chat/
├── server.py           # Chat server — accepts connections & broadcasts
├── client.py           # Chat client — encrypts/decrypts messages
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
└── README.md           # Documentation
```

## Tech Stack

- **Python** — standard library `socket` and `threading` modules
- **cryptography** — Fernet (AES-128-CBC + HMAC-SHA256)

## License

This project is licensed under the MIT License.
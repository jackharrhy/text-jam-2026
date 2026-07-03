import json
import threading

from pydantic import BaseModel

MAX_MESSAGE_SIZE = 8192


class SocketConnection:
    def __init__(self, sock):
        self.sock = sock

    def send(self, data: bytes):
        self.sock.sendall(data)

    def recv(self, size: int) -> bytes:
        return self.sock.recv(size)

    def close(self):
        self.sock.close()


class WebSocketConnection:
    def __init__(self, websocket):
        self.websocket = websocket
        self.send_lock = threading.Lock()

    def send(self, data: bytes):
        message = data.decode("utf-8").rstrip("\n")
        with self.send_lock:
            self.websocket.send(message)

    def recv(self, size: int) -> bytes:
        message = self.websocket.recv()

        if isinstance(message, bytes):
            payload = message.decode("utf-8")
        else:
            payload = message

        return f"{payload}\n".encode()

    def close(self):
        self.websocket.close()


def send_message(conn, msg: BaseModel):

    message = msg.model_dump_json(exclude_none=True) + "\n"

    conn.send(message.encode())


def receive_json(conn, buffer):

    while "\n" not in buffer:
        try:
            chunk = conn.recv(1024).decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Invalid UTF-8 received")

        if not chunk:
            return None, buffer

        buffer += chunk

        if len(buffer) > MAX_MESSAGE_SIZE:
            raise ValueError("Message exceeds maximum size")

    line, buffer = buffer.split("\n", 1)

    try:
        return json.loads(line), buffer
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON received")


def safe_send_message(player, msg: BaseModel):

    if not player.connected or not player.connection:
        return False

    try:
        send_message(player.connection, msg)
        return True

    except OSError:
        player.disconnect()
        return False


def safe_send_connection(conn, msg: BaseModel):
    if not conn:
        return False

    try:
        send_message(conn, msg)
        return True
    except OSError:
        return False

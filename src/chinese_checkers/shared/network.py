import json

from pydantic import BaseModel

MAX_MESSAGE_SIZE = 8192


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

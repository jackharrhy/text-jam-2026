import json

MAX_MESSAGE_SIZE = 8192


def send_json(conn, data):

    message = json.dumps(data) + "\n"

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


def safe_send_json(player, data):

    if not player.connected or not player.connection:
        return False

    try:
        send_json(player.connection, data)
        return True

    except OSError:
        player.disconnect()
        return False

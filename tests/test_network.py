from chinese_checkers.shared.models import ConnectMessage
from chinese_checkers.shared.network import (
    WebSocketConnection,
    receive_json,
    send_message,
)


class FakeWebSocket:
    def __init__(self, incoming=None):
        self.incoming = list(incoming or [])
        self.sent = []
        self.closed = False

    def recv(self):
        return self.incoming.pop(0)

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True


def test_websocket_connection_receives_text_frame_as_json_message():
    websocket = FakeWebSocket(
        ['{"type":"connect","protocol_version":2,"player_id":"p1","name":"Ada"}']
    )
    connection = WebSocketConnection(websocket)

    data, buffer = receive_json(connection, "")

    assert data == {
        "type": "connect",
        "protocol_version": 2,
        "player_id": "p1",
        "name": "Ada",
    }
    assert buffer == ""


def test_websocket_connection_sends_json_text_frame_without_newline():
    websocket = FakeWebSocket()
    connection = WebSocketConnection(websocket)

    send_message(
        connection,
        ConnectMessage(protocol_version=2, player_id="p1", name="Ada"),
    )

    assert websocket.sent == [
        '{"type":"connect","protocol_version":2,"player_id":"p1","name":"Ada","spectator":false}'
    ]


def test_websocket_connection_close_delegates_to_websocket():
    websocket = FakeWebSocket()
    connection = WebSocketConnection(websocket)

    connection.close()

    assert websocket.closed is True

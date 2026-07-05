import asyncio

import pytest

from chinese_checkers.server.web import BrowserConnection
from chinese_checkers.shared.models import ConnectMessage
from chinese_checkers.shared.network import receive_json, send_message


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send_text(self, message):
        self.sent.append(message)

    async def close(self):
        self.closed = True


@pytest.mark.anyio
async def test_browser_connection_receives_text_frame_as_json_message():
    conn = BrowserConnection(FakeWebSocket())
    conn.receive_text(
        '{"type":"connect","protocol_version":2,"player_id":"p1","name":"Ada"}'
    )

    data, buffer = receive_json(conn, "")

    assert data == {
        "type": "connect",
        "protocol_version": 2,
        "player_id": "p1",
        "name": "Ada",
    }
    assert buffer == ""


@pytest.mark.anyio
async def test_browser_connection_sends_json_text_frame_without_newline():
    websocket = FakeWebSocket()
    conn = BrowserConnection(websocket)

    send_message(
        conn,
        ConnectMessage(protocol_version=2, player_id="p1", name="Ada"),
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert websocket.sent == [
        '{"type":"connect","protocol_version":2,"player_id":"p1","name":"Ada","spectator":false}'
    ]


@pytest.mark.anyio
async def test_browser_connection_close_closes_websocket_and_unblocks_recv():
    websocket = FakeWebSocket()
    conn = BrowserConnection(websocket)

    conn.close()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert conn.recv(1024) == b""
    assert websocket.closed is True


@pytest.mark.anyio
async def test_browser_connection_uses_shared_message_size_limit():
    conn = BrowserConnection(FakeWebSocket())
    conn.receive_text("{" + (" " * 8192) + "}")

    with pytest.raises(ValueError, match="Message exceeds maximum size"):
        receive_json(conn, "")

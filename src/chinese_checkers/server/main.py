import socket
import threading
import time

import uvicorn

from chinese_checkers.server.protocol import handle_connection
from chinese_checkers.server.session_manager import SessionManager
from chinese_checkers.server.web import create_app
from chinese_checkers.shared.models import ServerHeartbeatMessage
from chinese_checkers.shared.network import (
    SocketConnection,
    safe_send_message,
)
from chinese_checkers.shared.settings import (
    ENABLE_WEBSOCKET_SERVER,
    HEARTBEAT_INTERVAL,
    LISTEN_HOST,
    SERVER_PORT,
    WEBSOCKET_LISTEN_HOST,
    WEBSOCKET_PORT,
)

manager = SessionManager()


def start_web_server():
    app = create_app(manager)
    config = uvicorn.Config(
        app,
        host=WEBSOCKET_LISTEN_HOST,
        port=WEBSOCKET_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


def start_server():

    if ENABLE_WEBSOCKET_SERVER and WEBSOCKET_PORT == SERVER_PORT:
        print(
            "Server.py: browser listener disabled because WEBSOCKET_PORT matches "
            "SERVER_PORT. Use a separate port or add a protocol multiplexer."
        )

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, SERVER_PORT))
    server.listen()

    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)

    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)

    heartbeat_thread.start()

    cleanup_thread.start()

    if ENABLE_WEBSOCKET_SERVER and WEBSOCKET_PORT != SERVER_PORT:
        web_thread = threading.Thread(target=start_web_server, daemon=True)
        web_thread.start()

    print(f"Server.py: TCP server started on {LISTEN_HOST}:{SERVER_PORT}")

    try:
        while True:
            conn, addr = server.accept()

            print(f"Server.py: New connection: {addr}")

            thread = threading.Thread(
                target=handle_connection,
                args=(manager, SocketConnection(conn)),
            )

            thread.start()

    except KeyboardInterrupt:
        print("\nShutting down server...")

    finally:
        server.close()

        print("server closed.")


def heartbeat_loop():

    while True:
        time.sleep(HEARTBEAT_INTERVAL)

        with manager.lock:
            sessions = list(manager.sessions.values())

        for session in sessions:
            for player in session.players.values():
                if player.connected and player.connection:
                    safe_send_message(player, ServerHeartbeatMessage())


def cleanup_loop():

    while True:
        manager.cleanup_sessions()

        time.sleep(10)


def main():
    start_server()


if __name__ == "__main__":
    start_server()

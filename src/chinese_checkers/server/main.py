import socket
import threading
import time
import traceback

from websockets.sync.server import serve

from chinese_checkers.game.player import Player
from chinese_checkers.server.session_manager import SessionManager
from chinese_checkers.server.session_states import IN_PROGRESS
from chinese_checkers.shared.models import (
    ClientChatMessage,
    ConnectMessage,
    DebugMessage,
    DuplicatePlayerMessage,
    ErrorMessage,
    InvalidSessionMessage,
    LeaveGameMessage,
    LeaveLobbyMessage,
    ServerHeartbeatMessage,
    SessionValidatedMessage,
    WelcomeMessage,
    client_adapter,
)
from chinese_checkers.shared.network import (
    SocketConnection,
    WebSocketConnection,
    receive_json,
    safe_send_message,
    send_message,
)
from chinese_checkers.shared.settings import (
    ENABLE_WEBSOCKET_SERVER,
    HEARTBEAT_INTERVAL,
    LISTEN_HOST,
    PROTOCOL_VERSION,
    SERVER_PORT,
    WEBSOCKET_LISTEN_HOST,
    WEBSOCKET_PORT,
)

manager = SessionManager()


def handle_connection(manager, conn):

    buffer = ""

    try:
        data, buffer = receive_json(conn, buffer)
        client_msg = client_adapter.validate_python(data)

    except ValueError as e:
        print(f"Rejected connection: {e}")

        conn.close()

        return
    except (ConnectionResetError, OSError):
        conn.close()
        return

    if data is None:
        conn.close()
        return

    if not isinstance(client_msg, ConnectMessage):
        conn.close()
        return

    client_version = client_msg.protocol_version

    if client_version != PROTOCOL_VERSION:
        send_message(conn, ErrorMessage(message="Client version mismatch."))

        conn.close()
        return

    player_id = client_msg.player_id
    session_id = client_msg.session_id
    session = None

    if client_msg.spectator:
        handle_spectator_connection(manager, conn, client_msg, buffer)
        return

    # Identity file has session id
    if session_id:
        session = manager.get_session(session_id)

        # Session ID belongs to expired / invalid session.
        if session is None:
            send_message(conn, InvalidSessionMessage())
            conn.close()
            return

        session_players = session.get_connected_players()

        # Trying to connect to session while already connected (Duplicate player).
        if player_id in session_players:
            send_message(conn, DuplicatePlayerMessage())
            conn.close()
            return

        # Session is valid
        player_num = session.get_player_num(player_id)
        send_message(conn, SessionValidatedMessage.for_session(session, player_num))

    # Player created a new session
    if session is None:
        num_players = client_msg.num_players or 2
        session = manager.create_session(num_players)
        session_id = session.session_id

    # Reconnect player to valid session
    if player_id in session.players:
        player = session.players[player_id]
        player.attach_connection(conn)

        player.last_seen = time.time()
        session.touch()

        session.handle_reconnect(player)
        print(
            f"\nPlayer id {player_id} reconnected to Session id: {session.session_id}"
        )

    # New player connecting to session
    else:
        player = Player(player_id, client_msg.name, session.session_id)
        player.attach_connection(conn)
        player.last_seen = time.time()
        session.add_player(player)
        print(f"\nPlayer id: {player_id} connected to Session id: {session.session_id}")
        send_message(conn, WelcomeMessage.for_player(player, session))

    buffer = ""
    player_exit_type = None

    # Receive message loop
    while True:
        try:
            data, buffer = receive_json(conn, buffer)

            if data is None:
                break

            client_msg = client_adapter.validate_python(data)

            if isinstance(client_msg, DebugMessage):
                print("DEBUG: ", client_msg.message)

                continue

            if isinstance(client_msg, LeaveLobbyMessage):
                player_exit_type = "lobby"
                break

            if isinstance(client_msg, LeaveGameMessage):
                player_exit_type = "game"
                break

            session.handle_message(player, client_msg)

        except ValueError as e:
            print("\nClient sent invalid/oversized message:", e)
            break

        except Exception as e:
            print("\nError: server receive loop:", e)
            traceback.print_exc()
            break

    if player_exit_type == "lobby":
        print(f"Server.py: Player {player.player_id} left the lobby")
        session.handle_leave_lobby(player)

    elif player_exit_type == "game":
        print(f"Server.py: Player {player.player_id} left the game")
        session.handle_leave_game(player)

    else:
        session.handle_disconnect(player)
        print(f"Server.py: Player {player.player_id} disconnected")

    conn.close()


def handle_spectator_connection(manager, conn, connect_msg, buffer):
    if not connect_msg.session_id:
        send_message(
            conn, ErrorMessage(message="Spectators must provide a session ID.")
        )
        conn.close()
        return

    session = manager.get_session(connect_msg.session_id)

    if session is None:
        send_message(conn, InvalidSessionMessage())
        conn.close()
        return

    if session.state != IN_PROGRESS:
        send_message(
            conn, ErrorMessage(message="Spectators can only join active games.")
        )
        conn.close()
        return

    send_message(
        conn,
        SessionValidatedMessage.for_session(session, None),
    )
    session.add_spectator(connect_msg.player_id, conn)

    while True:
        try:
            data, buffer = receive_json(conn, buffer)

            if data is None:
                break

            client_msg = client_adapter.validate_python(data)

            if isinstance(client_msg, DebugMessage):
                print("DEBUG: ", client_msg.message)
                continue

            if isinstance(client_msg, LeaveGameMessage):
                break

            if isinstance(client_msg, ClientChatMessage):
                session.handle_spectator_chat(connect_msg.name, client_msg)

        except ValueError as e:
            print("\nSpectator sent invalid/oversized message:", e)
            break
        except Exception as e:
            print("\nError: spectator receive loop:", e)
            traceback.print_exc()
            break

    session.remove_spectator(connect_msg.player_id)
    conn.close()


def handle_websocket_connection(websocket):
    print("Server.py: New WebSocket connection")
    handle_connection(manager, WebSocketConnection(websocket))


def start_websocket_server():
    try:
        with serve(
            handle_websocket_connection,
            WEBSOCKET_LISTEN_HOST,
            WEBSOCKET_PORT,
        ) as websocket_server:
            print(
                "Server.py: WebSocket server started "
                f"on {WEBSOCKET_LISTEN_HOST}:{WEBSOCKET_PORT}"
            )
            websocket_server.serve_forever()
    except OSError as e:
        print(f"Server.py: WebSocket server failed to start: {e}")


def start_server():

    if ENABLE_WEBSOCKET_SERVER and WEBSOCKET_PORT == SERVER_PORT:
        print(
            "Server.py: WebSocket listener disabled because WEBSOCKET_PORT matches "
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
        websocket_thread = threading.Thread(target=start_websocket_server, daemon=True)
        websocket_thread.start()

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

import time
import traceback

from chinese_checkers.game.player import Player
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
    SessionValidatedMessage,
    WelcomeMessage,
    client_adapter,
)
from chinese_checkers.shared.network import receive_json, send_message
from chinese_checkers.shared.settings import PROTOCOL_VERSION


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

    if client_msg.protocol_version != PROTOCOL_VERSION:
        send_message(conn, ErrorMessage(message="Client version mismatch."))
        conn.close()
        return

    player_id = client_msg.player_id
    session_id = client_msg.session_id
    session = None

    if client_msg.spectator:
        handle_spectator_connection(manager, conn, client_msg, buffer)
        return

    if session_id:
        session = manager.get_session(session_id)

        if session is None:
            send_message(conn, InvalidSessionMessage())
            conn.close()
            return

        if player_id in session.get_connected_players():
            send_message(conn, DuplicatePlayerMessage())
            conn.close()
            return

        player_num = session.get_player_num(player_id)
        send_message(conn, SessionValidatedMessage.for_session(session, player_num))

    if session is None:
        session = manager.create_session(client_msg.num_players or 2)

    if player_id in session.players:
        player = session.players[player_id]
        player.attach_connection(conn)
        player.last_seen = time.time()
        session.touch()
        session.handle_reconnect(player)
        print(f"\nPlayer id {player_id} reconnected to Session id: {session.session_id}")
    else:
        player = Player(player_id, client_msg.name, session.session_id)
        player.attach_connection(conn)
        player.last_seen = time.time()
        session.add_player(player)
        print(f"\nPlayer id: {player_id} connected to Session id: {session.session_id}")
        send_message(conn, WelcomeMessage.for_player(player, session))

    buffer = ""
    player_exit_type = None

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

    send_message(conn, SessionValidatedMessage.for_session(session, None))
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

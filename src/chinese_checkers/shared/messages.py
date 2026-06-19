import time

from chinese_checkers.shared.message_types import (
    GAME_STATE,
    ERROR,
    WELCOME,
    LOBBY_STATE,
    PARTIAL_VALIDATION,
    GAME_STARTED,
    PLAYER_RECONNECTED,
    PLAYER_DISCONNECTED,
    SESSION_VALIDATED,
    INVALID_SESSION,
    DUPLICATE_PLAYER,
    PLAYER_JOINED_GAME,
    SERVER_HEARTBEAT,
    KICKED_FROM_LOBBY,
    LEAVE_GAME,
    PLAYER_QUIT,
    CHAT,
)


def make_error(message):

    return {"type": ERROR, "message": message}


def make_game_state(game_state):

    return {
        "type": GAME_STATE,
        "board": game_state.serialize_board(),
        "current_player": game_state.current_player_number,
        "winner": game_state.winner,
    }


def make_welcome(player, session):

    player_configs = []

    if session.game_state:
        player_configs = session.game_state.players

    return {
        "type": WELCOME,
        "player_id": player.player_id,
        "player_number": player.player_number,
        "players": player_configs,
        "session_id": session.session_id,
        "chat_history": session.chat_history,
    }


def make_lobby_state(session, player):

    return {
        "type": LOBBY_STATE,
        "players": session.serialize_players(),
        "session_id": session.session_id,
        "num_players": session.lobby_num_players,
        "is_host": session.host_player_id == player.player_id,
    }


def make_partial_validation(valid, message):

    return {"type": PARTIAL_VALIDATION, "valid": valid, "message": message}


def make_game_started(session, player):

    return {
        "type": GAME_STARTED,
        "player_number": player.player_number,
        "player_configs": session.game_state.players,
    }


def make_player_joined_game(player):

    return {
        "type": PLAYER_JOINED_GAME,
        "player_name": player.name,
        "player_number": player.player_number,
    }


def make_player_reconnected(player):

    return {
        "type": PLAYER_RECONNECTED,
        "player_name": player.name,
        "player_number": player.player_number,
    }


def make_kicked_from_lobby():

    return {"type": KICKED_FROM_LOBBY}


def make_leave_game():
    return {"type": LEAVE_GAME}


def make_player_disconnected(player):

    return {
        "type": PLAYER_DISCONNECTED,
        "player_name": player.name,
        "player_number": player.player_number,
    }


def make_player_quit(player):
    return {
        "type": PLAYER_QUIT,
        "player_name": player.name,
        "player_number": player.player_number,
    }


def make_chat(player, message):
    return {
        "type": CHAT,
        "player_name": player.name,
        "player_number": player.player_number,
        "message": message,
        "timestamp": time.time(),
    }


def make_server_heartbeat():

    return {"type": SERVER_HEARTBEAT}


def make_invalid_session():

    return {"type": INVALID_SESSION}


def make_session_validated(session, player_num):

    player_configs = []

    if session.game_state:
        player_configs = session.game_state.players

    return {
        "type": SESSION_VALIDATED,
        "session_state": session.state,
        "num_players": session.lobby_num_players,
        "player_num": player_num,
        "player_configs": player_configs,
    }


def make_duplicate_player():

    return {"type": DUPLICATE_PLAYER}

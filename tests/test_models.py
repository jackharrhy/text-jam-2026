import json

import pytest

from chinese_checkers.shared.models import (
    ClientChatMessage,
    ClientMessage,
    ConnectMessage,
    ErrorMessage,
    GameStartedMessage,
    GameStateMessage,
    Identity,
    KickPlayerMessage,
    LeaveLobbyMessage,
    LobbyPlayer,
    LobbyStateMessage,
    MoveMessage,
    PlayerConfig,
    PlayerJoinedGameMessage,
    ServerHeartbeatMessage,
    ServerMessage,
    StartGameMessage,
    UpdateNumPlayersMessage,
    WelcomeMessage,
    client_adapter,
    server_adapter,
)


class TestIdentity:
    def test_create_and_serialize(self):
        i = Identity(player_id="abc", name="Alice")
        assert i.player_id == "abc"
        assert i.name == "Alice"
        assert i.session_id is None

    def test_json_roundtrip(self):
        i = Identity(
            player_id="abc", name="Alice", session_id="SESS"
        )
        dumped = i.model_dump_json()
        loaded = Identity.model_validate_json(dumped)
        assert loaded.player_id == "abc"
        assert loaded.name == "Alice"
        assert loaded.session_id == "SESS"

    def test_json_roundtrip_no_session(self):
        i = Identity(player_id="abc", name="Alice")
        dumped = i.model_dump_json()
        loaded = Identity.model_validate_json(dumped)
        assert loaded.session_id is None


class TestPlayerConfig:
    def test_model(self):
        pc = PlayerConfig(player=1, start="N", goal="S", piece="red")
        assert pc.player == 1
        assert pc.start == "N"


class TestLobbyPlayer:
    def test_model(self):
        lp = LobbyPlayer(
            player_id="p1", name="Alice", player_number=1,
            connected=True, is_host=True,
        )
        assert lp.player_id == "p1"
        assert lp.player_number == 1
        assert lp.is_cpu is False

    def test_cpu_flag(self):
        lp = LobbyPlayer(
            player_id="cpu1", name="Luna [CPU]", player_number=2,
            connected=True, is_host=False, is_cpu=True,
        )
        assert lp.is_cpu is True


class TestClientMessages:
    def test_connect_message(self):
        msg = ConnectMessage(
            protocol_version=2, player_id="p1", name="Alice",
            num_players=4,
        )
        assert msg.type == "connect"
        assert msg.session_id is None

    def test_move_message(self):
        msg = MoveMessage(path=[[0, 0], [1, 1]])
        assert msg.type == "move"
        assert msg.path == [[0, 0], [1, 1]]

    def test_start_game_with_cpus(self):
        msg = StartGameMessage(cpu_count=3)
        assert msg.cpu_count == 3

    def test_start_game_default_cpu(self):
        msg = StartGameMessage()
        assert msg.cpu_count == 0

    def test_empty_messages(self):
        for cls in [
            StartGameMessage, LeaveLobbyMessage,
        ]:
            msg = cls()
            assert msg.model_dump_json()

    def test_client_adapter_connect(self):
        data = {
            "type": "connect", "protocol_version": 2,
            "player_id": "p1", "name": "Alice",
            "num_players": 4, "cpu_count": 2,
        }
        msg = client_adapter.validate_python(data)
        assert isinstance(msg, ConnectMessage)
        assert msg.num_players == 4

    def test_client_adapter_move(self):
        data = {"type": "move", "path": [[0, 0], [1, 1]]}
        msg = client_adapter.validate_python(data)
        assert isinstance(msg, MoveMessage)

    def test_client_adapter_chat(self):
        data = {"type": "chat", "message": "hello"}
        msg = client_adapter.validate_python(data)
        assert isinstance(msg, ClientChatMessage)
        assert msg.message == "hello"

    def test_client_adapter_invalid_type(self):
        with pytest.raises(Exception):
            client_adapter.validate_python({"type": "nonexistent"})


class TestServerMessages:
    def test_lobby_state(self):
        msg = LobbyStateMessage(
            players=[], session_id="SESS",
            num_players=4, is_host=True,
        )
        assert msg.num_players == 4

    def test_game_state(self):
        msg = GameStateMessage(
            board={}, current_player=1,
        )
        assert msg.winner is None

    def test_game_started(self):
        msg = GameStartedMessage(
            player_number=2,
            player_configs=[
                PlayerConfig(player=1, start="N", goal="S", piece="red"),
                PlayerConfig(player=2, start="S", goal="N", piece="green"),
            ],
        )
        assert msg.player_number == 2
        assert len(msg.player_configs) == 2

    def test_error(self):
        msg = ErrorMessage(message="test error")
        assert msg.message == "test error"

    def test_heartbeat(self):
        msg = ServerHeartbeatMessage()
        assert msg.type == "server_heartbeat"

    def test_welcome(self):
        msg = WelcomeMessage(
            player_id="p1", player_number=1,
            players=[], session_id="SESS", chat_history=[],
        )
        assert msg.player_number == 1

    def test_server_adapter_lobby_state(self):
        data = {
            "type": "lobby_state", "players": [],
            "session_id": "SESS", "num_players": 2,
            "is_host": True,
        }
        msg = server_adapter.validate_python(data)
        assert isinstance(msg, LobbyStateMessage)

    def test_server_adapter_game_state(self):
        data = {
            "type": "game_state",
            "board": {"0,0": 1, "1,0": None},
            "current_player": 1,
        }
        msg = server_adapter.validate_python(data)
        assert isinstance(msg, GameStateMessage)
        assert msg.board == {"0,0": 1, "1,0": None}

    def test_server_adapter_chat(self):
        data = {
            "type": "chat", "player_name": "Alice",
            "player_number": 1, "message": "hello",
            "timestamp": 1234567890.0,
        }
        msg = server_adapter.validate_python(data)
        from chinese_checkers.shared.models import ServerChatMessage
        assert isinstance(msg, ServerChatMessage)
        assert msg.player_name == "Alice"


class TestSendMessageExcludesNone:
    """Verify that model_dump_json(exclude_none=True) strips None fields."""
    def test_connect_excludes_none(self):
        msg = ConnectMessage(
            protocol_version=2, player_id="p1", name="Alice",
        )
        dumped = msg.model_dump_json(exclude_none=True)
        data = json.loads(dumped)
        assert "session_id" not in data
        assert "num_players" not in data

    def test_start_game_includes_zero_cpu(self):
        msg = StartGameMessage(cpu_count=0)
        dumped = msg.model_dump_json(exclude_none=True)
        data = json.loads(dumped)
        assert data["cpu_count"] == 0

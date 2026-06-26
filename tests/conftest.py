import uuid

import pytest

from chinese_checkers.game.game_state import GameState
from chinese_checkers.game.player import Player
from chinese_checkers.shared.models import Identity, PlayerConfig
from chinese_checkers.server.session import Session


@pytest.fixture
def player_configs_2():
    return [
        PlayerConfig(player=1, start="N", goal="S", piece="red"),
        PlayerConfig(player=2, start="S", goal="N", piece="green"),
    ]


@pytest.fixture
def player_configs_4():
    return [
        PlayerConfig(player=1, start="NW", goal="SE", piece="red"),
        PlayerConfig(player=2, start="NE", goal="SW", piece="blue"),
        PlayerConfig(player=3, start="SE", goal="NW", piece="green"),
        PlayerConfig(player=4, start="SW", goal="NE", piece="orange"),
    ]


@pytest.fixture
def game_state_2p():
    return GameState(2)


@pytest.fixture
def game_state_4p():
    return GameState(4)


@pytest.fixture
def identity():
    return Identity(player_id=str(uuid.uuid4()), name="TestPlayer")


@pytest.fixture
def session_2p():
    s = Session(session_id="TEST", num_players=2)
    p = Player(player_id="host1", name="Host", session_id="TEST")
    p.connected = True
    s.add_player(p)
    return s


@pytest.fixture
def session_2p_with_cpu():
    s = Session(session_id="TEST", num_players=2, cpu_count=1)
    p = Player(player_id="host1", name="Host", session_id="TEST")
    p.connected = True
    s.add_player(p)
    return s


@pytest.fixture
def human_player():
    p = Player(
        player_id="hp1", name="Human", session_id="TEST", player_number=1
    )
    p.connected = True
    return p


@pytest.fixture
def cpu_player():
    p = Player(
        player_id="cpu1", name="Luna [CPU]", session_id="TEST",
        player_number=2, is_cpu=True,
    )
    p.connected = True
    return p

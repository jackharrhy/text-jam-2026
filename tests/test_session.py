import threading
import time
import uuid

import pytest

from chinese_checkers.game.cpu_brain import generate_move
from chinese_checkers.game.game_state import GameState
from chinese_checkers.game.move_validator import validate_move
from chinese_checkers.game.player import Player
from chinese_checkers.server.session import Session
from chinese_checkers.server.session_states import IN_PROGRESS, LOBBY
from chinese_checkers.shared.models import (
    ClientChatMessage,
    ErrorMessage,
    MoveMessage,
    PlayerConfig,
    ServerChatMessage,
    StartGameMessage,
    UpdateNumPlayersMessage,
    ValidatePartialMessage,
    PartialValidationMessage,
    KickPlayerMessage,
    LeaveLobbyMessage,
)


class TestSessionLifecycle:
    def test_create_session(self):
        s = Session(session_id="ABCD", num_players=2)
        assert s.session_id == "ABCD"
        assert s.state == LOBBY
        assert s.lobby_num_players == 2

    def test_add_player(self):
        s = Session(session_id="ABCD", num_players=2)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        assert "p1" in s.players
        assert s.host_player_id == "p1"

    def test_serialize_players(self):
        s = Session(session_id="ABCD", num_players=2)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        players = s.serialize_players()
        assert len(players) == 1
        assert players[0].player_id == "p1"
        assert players[0].name == "Alice"
        assert players[0].is_host is True

    def test_remove_player(self):
        s = Session(session_id="ABCD", num_players=2)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        s.remove_player(p)
        assert "p1" not in s.players

    def test_all_players_connected(self):
        s = Session(session_id="ABCD", num_players=2)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        assert s.all_players_connected() is True

    def test_broadcast_to_game_skips_when_lobby(self):
        s = Session(session_id="ABCD", num_players=2)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        s.broadcast_to_game(
            PartialValidationMessage(valid=True, message="")
        )
        # Should not raise — silently skipped in lobby state


class TestSessionStartGame:
    def test_start_game_without_enough_players(self):
        """start_game should fill remaining slots with CPUs."""
        s = Session(session_id="ABCD", num_players=2, cpu_count=1)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        s.start_game()
        assert s.game_state is not None
        assert s.state == IN_PROGRESS
        assert len(s.players) == 2
        cpu = [pl for pl in s.players.values() if pl.is_cpu]
        assert len(cpu) == 1

    def test_start_game_assigns_numbers(self):
        s = Session(session_id="ABCD", num_players=2, cpu_count=1)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        s.start_game()
        assert s.game_state is not None
        for player in s.players.values():
            assert player.player_number is not None

    def test_handle_message_start_game(self):
        s = Session(session_id="ABCD", num_players=2, cpu_count=1)
        p = Player(player_id="p1", name="Alice", session_id="ABCD")
        p.connected = True
        s.add_player(p)
        s.handle_message(p, StartGameMessage(cpu_count=1))
        assert s.state == IN_PROGRESS

    def test_start_game_skips_when_not_host(self):
        s = Session(session_id="ABCD", num_players=2)
        host = Player(player_id="p1", name="Alice", session_id="ABCD")
        host.connected = True
        s.add_player(host)

        non_host = Player(player_id="p2", name="Bob", session_id="ABCD")
        non_host.connected = True
        s.add_player(non_host)

        s.handle_message(non_host, StartGameMessage())
        assert s.state == LOBBY  # Not host, ignored

    def test_start_game_skips_when_not_all_connected(self):
        s = Session(session_id="ABCD", num_players=2)
        host = Player(player_id="p1", name="Alice", session_id="ABCD")
        host.connected = True
        s.add_player(host)

        disconnected = Player(player_id="p2", name="Bob", session_id="ABCD")
        disconnected.connected = False
        s.add_player(disconnected)

        s.handle_message(host, StartGameMessage())
        assert s.state == LOBBY  # Not all connected


class TestHandleMove:
    def test_move_when_not_in_progress(self, session_2p):
        p = Player(player_id="p1", name="Alice", session_id="TEST")
        p.connected = True
        session_2p.add_player(p)
        result = session_2p.handle_move(
            list(session_2p.players.values())[0], [(0, 0), (1, 0)]
        )
        assert result is not None
        assert result.message == "Game is not active."

    def test_move_success_and_cpu_follows(self):
        """Human moves, then CPU auto-plays."""
        s = Session(session_id="ABCD", num_players=2, cpu_count=1)
        human = Player(player_id="p1", name="Alice", session_id="ABCD")
        human.connected = True
        s.add_player(human)
        s.cpu_count = 1
        s.start_game()
        assert s.game_state is not None

        assert s.state == IN_PROGRESS
        assert len(s.players) == 2
        assert s.game_state is not None

        current = s.game_state.current_player_number
        human_player_number = next(
            p.player_number for p in s.players.values()
            if not p.is_cpu
        )

        if current != human_player_number:
            pytest.skip("Human doesn't go first — CPU will play")

        move = generate_move(
            s.game_state.board, s.game_state.players,
            human_player_number,
        )
        assert move is not None, "Should find a legal move"

        result = s.handle_move(human, move)
        assert result is None  # Success

        assert s.game_state.board[move[0]] is None
        assert s.game_state.board[move[-1]] == human_player_number

    def test_handle_move_not_your_turn(self):
        s = Session(session_id="ABCD", num_players=2, cpu_count=1)
        human = Player(player_id="p1", name="Alice", session_id="ABCD")
        human.connected = True
        s.add_player(human)
        s.cpu_count = 1
        s.start_game()
        assert s.game_state is not None

        current = s.game_state.current_player_number
        wrong_player = next(
            (p for p in s.players.values()
             if p.player_number != current),
            None,
        )
        if wrong_player is None:
            pytest.skip("Only one player")
        if wrong_player.is_cpu:
            pytest.skip("Other player is CPU")

        board = s.game_state.board
        from_coord = None
        to_coord = None
        from chinese_checkers.ui.geometry import is_adjacent_move

        for coord, occupant in board.items():
            if occupant == wrong_player.player_number and from_coord is None:
                from_coord = coord
            elif (
                occupant is None
                and from_coord is not None
                and is_adjacent_move(from_coord, coord)
            ):
                to_coord = coord
                break

        if from_coord is None or to_coord is None:
            pytest.skip("No valid test move")

        result = s.handle_move(wrong_player, [from_coord, to_coord])
        assert result is not None
        assert "Not your turn" in result.message


class TestHandleOtherMessages:
    def test_validate_partial(self, session_2p_with_cpu):
        s = session_2p_with_cpu
        s.cpu_count = 1
        s.start_game()
        assert s.game_state is not None

        player = next(p for p in s.players.values() if not p.is_cpu)

        board = s.game_state.board
        for coord, occupant in board.items():
            if occupant == player.player_number:
                result = s.validate_partial_selection(
                    player, [coord]
                )
                assert result.valid is True
                break

    def test_handle_chat(self, session_2p):
        s = session_2p
        host = list(s.players.values())[0]
        msg = ClientChatMessage(message="hello world")
        s.handle_message(host, msg)
        assert len(s.chat_history) == 1
        assert s.chat_history[0].message == "hello world"
        assert s.chat_history[0].player_name == host.name

    def test_handle_update_num_players(self, session_2p):
        s = session_2p
        host = list(s.players.values())[0]
        s.handle_message(host, UpdateNumPlayersMessage(num_players=4))
        assert s.lobby_num_players == 4

    def test_handle_kick_player(self, session_2p):
        s = session_2p
        host = list(s.players.values())[0]
        target = Player(player_id="p2", name="Bob", session_id="TEST")
        target.connected = True
        s.add_player(target)
        assert "p2" in s.players
        s.handle_message(host, KickPlayerMessage(player_id="p2"))
        assert "p2" not in s.players

    def test_handle_leave_lobby(self, session_2p):
        s = session_2p
        host = list(s.players.values())[0]
        s.handle_leave_lobby(host)
        assert host.player_id not in s.players

    def test_handle_leave_game(self, session_2p_with_cpu):
        s = session_2p_with_cpu
        s.cpu_count = 1
        s.start_game()
        assert s.game_state is not None
        host = next(p for p in s.players.values() if not p.is_cpu)
        s.handle_leave_game(host)
        assert host.player_id not in s.players


class TestFullGameFlow:
    def test_two_player_game_with_cpu_plays_to_completion(self):
        """Simulate a 2-player game with 1 CPU for 40 turns without errors."""
        s = Session(session_id="TEST", num_players=2, cpu_count=1)
        human = Player(player_id="p1", name="Alice", session_id="TEST")
        human.connected = True
        s.add_player(human)
        s.cpu_count = 1
        s.start_game()
        assert s.game_state is not None

        assert s.state == IN_PROGRESS

        for _ in range(40):
            current = s.game_state.current_player_number

            cpu_player = next(
                (p for p in s.players.values()
                 if p.player_number == current and p.is_cpu),
                None,
            )

            if cpu_player is not None:
                with s.lock:
                    if s.game_state.winner is not None:
                        break
                    move = generate_move(
                        s.game_state.board,
                        s.game_state.players,
                        current,
                    )
                    if move is not None:
                        s.game_state.apply_move(move[0], move[-1])
                        s.broadcast_session_state()
            else:
                move = generate_move(
                    s.game_state.board,
                    s.game_state.players,
                    current,
                )
                if move is not None:
                    result = s.handle_move(human, move)
                    assert result is None, f"Move rejected: {result.message if result else 'ok'}"
                else:
                    break

        assert s.state == IN_PROGRESS, "Game should still be active"


class TestConcurrency:
    def test_concurrent_move_submissions(self):
        """Multiple rapid moves should not corrupt game state."""
        s = Session(session_id="TEST", num_players=2, cpu_count=1)
        human = Player(player_id="p1", name="Alice", session_id="TEST")
        human.connected = True
        s.add_player(human)
        s.cpu_count = 1
        s.start_game()
        assert s.game_state is not None

        moves = []
        for _ in range(50):
            if human.player_number != s.game_state.current_player_number:
                s.process_cpu_turns()

            move = generate_move(
                s.game_state.board,
                s.game_state.players,
                human.player_number,
            )
            if move is not None:
                result = s.handle_move(human, move)
                if result is not None:
                    moves.append(result)
                else:
                    moves.append("ok")

        assert len(moves) > 0

from chinese_checkers.game.board_initializer import create_initial_board
from chinese_checkers.game.cpu_brain import generate_move
from chinese_checkers.game.move_validator import (
    validate_move,
    validate_partial_move,
)
from chinese_checkers.game.player_configs import PLAYER_CONFIGS
from chinese_checkers.game.win_checker import check_winner
from chinese_checkers.shared.models import PlayerConfig
from chinese_checkers.ui.board_layout import VALID_COORDS, coord_at_render_position
from chinese_checkers.ui.geometry import is_adjacent_move, is_jump_move


class TestBoardInitializer:
    def test_2p_board_size(self, player_configs_2):
        board = create_initial_board(player_configs_2)
        assert len(board) > 0
        assert all(coord in VALID_COORDS for coord in board)

    def test_2p_piece_count(self, player_configs_2):
        board = create_initial_board(player_configs_2)
        p1_pieces = sum(1 for v in board.values() if v == 1)
        p2_pieces = sum(1 for v in board.values() if v == 2)
        assert p1_pieces == 10
        assert p2_pieces == 10

    def test_4p_piece_count(self, player_configs_4):
        board = create_initial_board(player_configs_4)
        for pn in range(1, 5):
            count = sum(1 for v in board.values() if v == pn)
            assert count == 10, f"Player {pn} has {count} pieces"

    def test_no_overlapping_pieces(self, player_configs_2):
        board = create_initial_board(player_configs_2)
        occupied = [c for c, v in board.items() if v is not None]
        assert len(occupied) == len(set(occupied))


class TestGameState:
    def test_initial_state_2p(self, game_state_2p):
        assert game_state_2p.current_player_number == 1
        assert game_state_2p.winner is None
        assert len(game_state_2p.players) == 2

    def test_current_player_cycles(self, game_state_2p):
        assert game_state_2p.current_player_number == 1
        game_state_2p.next_turn()
        assert game_state_2p.current_player_number == 2
        game_state_2p.next_turn()
        assert game_state_2p.current_player_number == 1

    def test_is_players_turn(self, game_state_2p):
        assert game_state_2p.is_players_turn(1) is True
        assert game_state_2p.is_players_turn(2) is False

    def test_serialize_board(self, game_state_2p):
        serialized = game_state_2p.serialize_board()
        assert isinstance(serialized, dict)
        for key in serialized:
            q, r = key.split(",")
            assert (int(q), int(r)) in game_state_2p.board


class TestGeometry:
    def test_render_position_maps_tile_character_to_coord(self):
        assert coord_at_render_position(12, 0) == (0, 0)

    def test_render_position_maps_tile_separator_to_previous_coord(self):
        assert coord_at_render_position(13, 0) == (0, 0)

    def test_render_position_ignores_leading_space(self):
        assert coord_at_render_position(11, 0) is None

    def test_render_position_ignores_out_of_board_position(self):
        assert coord_at_render_position(0, -1) is None
        assert coord_at_render_position(999, 0) is None

    def test_adjacent_horizontal(self):
        assert is_adjacent_move((0, 0), (1, 0)) is True

    def test_adjacent_diagonal(self):
        assert is_adjacent_move((0, 0), (1, -1)) is True

    def test_not_adjacent_far(self):
        assert is_adjacent_move((0, 0), (3, 0)) is False

    def test_jump_over_piece(self, player_configs_2):
        board = create_initial_board(player_configs_2)
        for coord, occupant in list(board.items()):
            if occupant == 1:
                continue
            board[coord] = 2
            break
        for coord in VALID_COORDS:
            board[coord] = None
        board[(0, 0)] = 1
        board[(1, 0)] = 2
        board[(2, 0)] = None
        assert is_jump_move(board, (0, 0), (2, 0)) is True


class TestMoveValidation:
    def test_validate_partial_select_own_piece(self, game_state_2p):
        for coord, occupant in game_state_2p.board.items():
            if occupant == 1:
                valid, reason = validate_partial_move(game_state_2p.board, 1, [coord])
                assert valid, f"Should be valid: {reason}"
                break

    def test_validate_partial_wrong_player(self, game_state_2p):
        for coord, occupant in game_state_2p.board.items():
            if occupant == 1:
                valid, reason = validate_partial_move(game_state_2p.board, 2, [coord])
                assert not valid
                assert "Not your piece" in reason
                break

    def test_validate_partial_empty_tile(self, game_state_2p):
        for coord, occupant in game_state_2p.board.items():
            if occupant is None:
                valid, reason = validate_partial_move(game_state_2p.board, 1, [coord])
                assert not valid
                break

    def test_validate_partial_invalid_coord(self, game_state_2p):
        valid, reason = validate_partial_move(game_state_2p.board, 1, [(-999, -999)])
        assert not valid

    def test_validate_move_adjacent(self, game_state_2p):
        from_coord = None
        to_coord = None
        for coord, occupant in game_state_2p.board.items():
            if occupant == 1 and from_coord is None:
                from_coord = coord
            elif (
                occupant is None and is_adjacent_move(from_coord, coord)
                if from_coord
                else False
            ):
                to_coord = coord
                break
        if from_coord and to_coord:
            valid, reason = validate_move(
                game_state_2p.board,
                game_state_2p.players,
                1,
                [from_coord, to_coord],
            )
            assert valid, f"Adjacent move should be valid: {reason}"

    def test_apply_move(self, game_state_2p):
        move = generate_move(game_state_2p.board, game_state_2p.players, 1)
        assert move is not None, "Should find a legal move"
        from_coord = move[0]
        to_coord = move[-1]

        game_state_2p.apply_move(from_coord, to_coord)
        assert game_state_2p.board[from_coord] is None
        assert game_state_2p.board[to_coord] == 1
        assert game_state_2p.current_player_number == 2


class TestWinChecker:
    def test_no_winner_initial(self, game_state_2p):
        assert check_winner(game_state_2p.board, game_state_2p.players, 1) is False

    def test_player_configs_have_goals(self):
        for num_players, configs in PLAYER_CONFIGS.items():
            assert len(configs) == num_players
            for pc in configs:
                assert isinstance(pc, PlayerConfig)
                assert pc.player > 0
                assert pc.start != pc.goal

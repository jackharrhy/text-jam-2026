from chinese_checkers.game.cpu_brain import generate_move
from chinese_checkers.game.board_initializer import create_initial_board
from chinese_checkers.game.player_configs import PLAYER_CONFIGS


class TestCpuBrain:
    def test_generates_move_for_player_1(self):
        players = PLAYER_CONFIGS[2]
        board = create_initial_board(players)
        move = generate_move(board, players, 1)
        assert move is not None, "Should find at least one legal move"
        assert len(move) >= 2
        assert board[move[0]] == 1
        assert board[move[-1]] is None

    def test_generates_move_for_player_2(self):
        players = PLAYER_CONFIGS[2]
        board = create_initial_board(players)
        move = generate_move(board, players, 2)
        assert move is not None
        assert board[move[0]] == 2
        assert board[move[-1]] is None

    def test_move_is_valid(self):
        players = PLAYER_CONFIGS[2]
        board = create_initial_board(players)
        for _ in range(10):
            move = generate_move(board, players, 1)
            assert move is not None
            # Apply the move to advance the board for next iteration
            board[move[-1]] = board[move[0]]
            board[move[0]] = None

    def test_4p_generates_moves(self):
        players = PLAYER_CONFIGS[4]
        board = create_initial_board(players)
        for pn in range(1, 5):
            move = generate_move(board, players, pn)
            assert move is not None, f"Player {pn} should have legal moves"
            assert len(move) >= 2

    def test_6p_generates_moves(self):
        players = PLAYER_CONFIGS[6]
        board = create_initial_board(players)
        for pn in range(1, 7):
            move = generate_move(board, players, pn)
            assert move is not None, f"Player {pn} should have legal moves"

    def test_move_determinism_across_calls(self):
        """Multiple calls should produce different moves (randomness)."""
        players = PLAYER_CONFIGS[2]
        board = create_initial_board(players)

        moves = set()
        for _ in range(20):
            move = generate_move(board, players, 1)
            path_tuple = tuple(tuple(c) for c in move)
            moves.add(path_tuple)

        assert len(moves) > 1, "Should generate different moves"

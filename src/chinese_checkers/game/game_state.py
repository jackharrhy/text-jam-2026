from chinese_checkers.game.board_initializer import create_initial_board
from chinese_checkers.ui.geometry import (
    get_zone_for_coord,
    is_adjacent_move,
    is_jump_move,
)
from chinese_checkers.game.player_configs import PLAYER_CONFIGS
from chinese_checkers.game.win_checker import check_winner


class GameState:
    def __init__(self, num_players=2):

        self.players = PLAYER_CONFIGS[num_players]
        self.board = create_initial_board(self.players)
        self.current_player_index = 0

        self.winner = None

    @property
    def current_player(self):
        return self.players[self.current_player_index]

    @property
    def current_player_number(self):
        return self.current_player["player"]

    def is_players_turn(self, player_number):
        return player_number == self.current_player_number

    def apply_move(self, move_from, move_to):

        player_number = self.board[move_from]

        self.board[move_to] = player_number

        self.board[move_from] = None

        # Check for victory
        if check_winner(self.board, self.players, player_number):
            self.winner = player_number

            return

        # Next turn
        self.next_turn()

    def next_turn(self):

        self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def serialize_board(self):

        serialized = {}

        for coord, value in self.board.items():
            key = f"{coord[0]},{coord[1]}"
            serialized[key] = value

        return serialized

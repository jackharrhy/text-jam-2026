from chinese_checkers.ui.board_layout import HOME_ZONES, VALID_COORDS


def create_initial_board(players):

    board = {}

    for coord in VALID_COORDS:
        board[coord] = None

    for config in players:
        player_number = config.player
        start_zone = config.start

        for coord in HOME_ZONES[start_zone]:
            board[coord] = player_number

    return board

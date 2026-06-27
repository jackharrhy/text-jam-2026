from chinese_checkers.ui.board_layout import HOME_ZONES


def check_winner(board, players, player_number):

    player_config = next(p for p in players if p.player == player_number)

    target_zone_name = player_config.goal

    target_zone = HOME_ZONES[target_zone_name]

    player_positions = {
        coord for coord, piece in board.items() if piece == player_number
    }

    return player_positions == target_zone

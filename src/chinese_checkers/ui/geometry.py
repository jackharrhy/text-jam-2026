from chinese_checkers.ui.board_layout import HOME_ZONES

DIRECTIONS = {
    "w": (0, -1),
    "e": (1, -1),
    "d": (1, 0),
    "x": (0, 1),
    "z": (-1, 1),
    "a": (-1, 0),
}


def add_coords(a, b):

    return (a[0] + b[0], a[1] + b[1])


def get_zone_for_coord(coord):

    for zone_name, coords in HOME_ZONES.items():
        if coord in coords:
            return zone_name

    return None


def is_adjacent_move(move_from, move_to):

    for direction in DIRECTIONS.values():
        neighbor = add_coords(move_from, direction)

        if neighbor == move_to:
            return True

    return False


def is_jump_move(board, move_from, move_to):

    for direction in DIRECTIONS.values():
        middle = add_coords(move_from, direction)

        landing = add_coords(middle, direction)

        if landing == move_to and middle in board and board[middle] is not None:
            return True

    return False

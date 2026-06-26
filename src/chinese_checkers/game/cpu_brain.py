import random

from chinese_checkers.game.move_validator import validate_move
from chinese_checkers.ui.geometry import is_jump_move


def _find_jump_chains(board, start, visited=None):
    """DFS to find all reachable destinations via jump chains."""
    if visited is None:
        visited = {start}

    destinations = []

    # Try all six directions for jumps
    for offset in [
        (-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, -1)
    ]:
        neighbor = (start[0] + offset[0], start[1] + offset[1])
        landing = (neighbor[0] + offset[0], neighbor[1] + offset[1])

        if is_jump_move(board, start, landing) and landing not in visited:
            new_visited = visited | {landing}
            destinations.append(landing)

            destinations.extend(
                _find_jump_chains(board, landing, new_visited)
            )

    return destinations


def generate_move(board, players, player_number):
    """
    Generate a legal move for the CPU.
    Returns a list of [(q,r), ...] coordinates forming a valid move path,
    or None if no legal moves exist.
    """
    own_pieces = [
        coord for coord, occupant in board.items()
        if occupant == player_number
    ]

    if not own_pieces:
        return None

    all_moves = []

    for piece_coord in own_pieces:
        adjacent_destinations = []

        for offset in [
            (-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, -1)
        ]:
            dest = (piece_coord[0] + offset[0], piece_coord[1] + offset[1])

            if dest in board and board[dest] is None:
                path = [piece_coord, dest]
                valid, _ = validate_move(
                    board, players, player_number, path
                )
                if valid:
                    adjacent_destinations.append(path)

        all_moves.extend(adjacent_destinations)

        jump_destinations = _find_jump_chains(board, piece_coord)

        for dest in jump_destinations:
            path = [piece_coord, dest]
            valid, _ = validate_move(board, players, player_number, path)
            if valid:
                all_moves.append(path)

    if not all_moves:
        return None

    return random.choice(all_moves)

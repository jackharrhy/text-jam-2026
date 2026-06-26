from chinese_checkers.ui.geometry import (
    get_zone_for_coord,
    is_adjacent_move,
    is_jump_move,
)


def validate_partial_move(board, player_number, path):

    if len(path) < 1:
        return False, "Invalid selection."

    move_from = path[0]

    # Is source tile valid?
    if move_from not in board:
        return False, "Invalid source tile."

    # Is there actually a piece there?
    if board[move_from] is None:
        return False, "No piece there."

    # Is it player's piece?
    if board[move_from] != player_number:
        return False, "Not your piece."

    # Only selecting first tile
    if len(path) == 1:
        return True, ""

    # --------------
    # Adjacent move
    # --------------

    if len(path) == 2:
        destination = path[1]

        # Is destination tile valid?
        if destination not in board:
            return False, "Invalid destination tile."

        # Is destination occupied?
        if board[destination] is not None:
            return False, "Destination occupied."

        if is_adjacent_move(move_from, destination):
            return True, ""

    # -----------
    # Jump chain
    # -----------

    visited = {move_from}

    for i in range(len(path) - 1):
        current = path[i]
        nxt = path[i + 1]

        # Prevent loops
        if nxt in visited:
            return False, "Cannot revisit tiles."

        visited.add(nxt)

        # Destination must exist
        if nxt not in board:
            return False, "Invalid destination tile."

        # Destination must be empty
        if board[nxt] is not None:
            return False, "Destination occupied."

        # Must be a legal jump
        if not is_jump_move(board, current, nxt):
            return False, "Illegal jump."

    return True, ""


def validate_move(board, players, player_number, path):

    if len(path) < 2:
        return False, "Invalid move."

    # First validate the actual movement mechanics
    valid, reason = validate_partial_move(board, player_number, path)

    if not valid:
        return False, reason

    move_from = path[0]
    move_to = path[-1]

    from_zone = get_zone_for_coord(move_from)
    to_zone = get_zone_for_coord(move_to)

    player_config = next(p for p in players if p.player == player_number)

    start_zone = player_config.start
    target_zone = player_config.goal

    # Prevent returning to home triangle
    if from_zone is None and to_zone == start_zone:
        return False, "Cannot return to your starting triangle."

    # Prevent landing in non-target triangles
    if to_zone is not None and to_zone != start_zone and to_zone != target_zone:
        return False, "Cannot end move in opponent home triangle."

    # Once inside target triangle,
    # the piece cannot leave it
    if to_zone is None and from_zone == target_zone:
        return False, "Piece cannot leave goal zone."

    return True, ""

from chinese_checkers.ui.theme import COLORS

PLAYER_CONFIGS = {
    2: [
        {"player": 1, "start": "N", "goal": "S", "piece": COLORS["S"]["piece"]},
        {"player": 2, "start": "S", "goal": "N", "piece": COLORS["N"]["piece"]},
    ],
    3: [
        {"player": 1, "start": "N", "goal": "S", "piece": COLORS["S"]["piece"]},
        {"player": 2, "start": "SE", "goal": "NW", "piece": COLORS["NW"]["piece"]},
        {"player": 3, "start": "SW", "goal": "NE", "piece": COLORS["NE"]["piece"]},
    ],
    4: [
        {"player": 1, "start": "NW", "goal": "SE", "piece": COLORS["SE"]["piece"]},
        {"player": 2, "start": "NE", "goal": "SW", "piece": COLORS["SW"]["piece"]},
        {"player": 3, "start": "SE", "goal": "NW", "piece": COLORS["NW"]["piece"]},
        {"player": 4, "start": "SW", "goal": "NE", "piece": COLORS["NE"]["piece"]},
    ],
    6: [
        {"player": 1, "start": "N", "goal": "S", "piece": COLORS["S"]["piece"]},
        {"player": 2, "start": "NE", "goal": "SW", "piece": COLORS["SW"]["piece"]},
        {"player": 3, "start": "SE", "goal": "NW", "piece": COLORS["NW"]["piece"]},
        {"player": 4, "start": "S", "goal": "N", "piece": COLORS["N"]["piece"]},
        {"player": 5, "start": "SW", "goal": "NE", "piece": COLORS["NE"]["piece"]},
        {"player": 6, "start": "NW", "goal": "SE", "piece": COLORS["SE"]["piece"]},
    ],
}

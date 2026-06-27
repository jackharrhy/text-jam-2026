from chinese_checkers.shared.models import PlayerConfig
from chinese_checkers.ui.theme import COLORS

PLAYER_CONFIGS: dict[int, list[PlayerConfig]] = {
    2: [
        PlayerConfig(player=1, start="N", goal="S", piece=COLORS["S"]["piece"]),
        PlayerConfig(player=2, start="S", goal="N", piece=COLORS["N"]["piece"]),
    ],
    3: [
        PlayerConfig(player=1, start="N", goal="S", piece=COLORS["S"]["piece"]),
        PlayerConfig(player=2, start="SE", goal="NW", piece=COLORS["NW"]["piece"]),
        PlayerConfig(player=3, start="SW", goal="NE", piece=COLORS["NE"]["piece"]),
    ],
    4: [
        PlayerConfig(player=1, start="NW", goal="SE", piece=COLORS["SE"]["piece"]),
        PlayerConfig(player=2, start="NE", goal="SW", piece=COLORS["SW"]["piece"]),
        PlayerConfig(player=3, start="SE", goal="NW", piece=COLORS["NW"]["piece"]),
        PlayerConfig(player=4, start="SW", goal="NE", piece=COLORS["NE"]["piece"]),
    ],
    6: [
        PlayerConfig(player=1, start="N", goal="S", piece=COLORS["S"]["piece"]),
        PlayerConfig(player=2, start="NE", goal="SW", piece=COLORS["SW"]["piece"]),
        PlayerConfig(player=3, start="SE", goal="NW", piece=COLORS["NW"]["piece"]),
        PlayerConfig(player=4, start="S", goal="N", piece=COLORS["N"]["piece"]),
        PlayerConfig(player=5, start="SW", goal="NE", piece=COLORS["NE"]["piece"]),
        PlayerConfig(player=6, start="NW", goal="SE", piece=COLORS["SE"]["piece"]),
    ],
}

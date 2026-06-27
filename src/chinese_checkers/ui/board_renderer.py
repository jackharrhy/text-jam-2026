import math

from rich.style import Style
from rich.text import Text

from chinese_checkers.ui.board_layout import ROWS
from chinese_checkers.ui.geometry import get_zone_for_coord
from chinese_checkers.ui.theme import COLORS, CURSOR_PULSE_GREYS


class BoardRenderer:
    def build_board_text(
        self, board, player_configs, cursor=None, selected_path=None, tick=0
    ):

        PLAYER_STYLES = {
            config.player: Style(color=config.piece, bold=True)
            for config in player_configs
        }

        EMPTY_STYLE = Style(color="white")
        SELECTED_STYLE = Style(bgcolor="grey50")

        if selected_path is None:
            selected_path = []

        lines = []

        for row in ROWS:
            line = Text(" " * row["spacing"])

            for coord in row["tiles"]:
                occupant = board.get(coord)

                background_style = Style()
                overlay_style = Style()
                foreground_style = Style()

                home_zone = get_zone_for_coord(coord)

                if home_zone:
                    bg_color = COLORS[home_zone]["zone"]
                    background_style = Style(bgcolor=bg_color)

                # Cursor pulse highlight
                if coord == cursor:
                    phase = (math.sin(tick * 0.25) + 1) / 2

                    index = int(phase * (len(CURSOR_PULSE_GREYS) - 1))
                    pulse_color = CURSOR_PULSE_GREYS[index]

                    overlay_style = Style(
                        bgcolor=pulse_color, bold=True, underline=True
                    )

                # Selected path highlight
                # if coord in selected_path and coord != cursor: // Should we pulse on selected & cursor?
                if coord in selected_path:
                    overlay_style += SELECTED_STYLE

                if occupant is None:
                    foreground_style = EMPTY_STYLE
                    char = "○"

                elif occupant is not None:
                    foreground_style = PLAYER_STYLES.get(occupant, Style())
                    char = "●"

                final_style = background_style + overlay_style + foreground_style
                cell = Text(char, style=final_style)

                line.append(cell)
                line.append(" ")

            lines.append(line)

        output = Text()
        for i, line in enumerate(lines):
            output.append(line)
            if i != len(lines) - 1:
                output.append("\n")

        return output

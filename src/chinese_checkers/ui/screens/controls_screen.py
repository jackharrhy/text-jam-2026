from textual.app import ComposeResult
from textual.containers import CenterMiddle, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Markdown

CONTROLS_MARKDOWN = r"""
> **Move cursor**
```text
         (up-left)       (up-right)
                  \     /
              [W/K/Y] [E/U]
      (left) -- [A/H]     [D/L] -- (right)
              [Z/B] [X/J/N]
                  /     \
       (down-left)       (down-right)
```

> **Piece/Tile Selection/Deselection**
```text
    [SPACE] -- (select piece/tile)
    [CLICK] -- (select clicked piece/tile)
    [ESC]   -- (deselect last tile/piece)
    [TAB]   -- (cycle through pieces)
```

> **Submit move**
```text
    [ENTER/RETURN] -- (finalize move)
```
"""


class ControlsScreen(Screen):
    DEFAULT_CSS = """
    #controls_container {
    width: 60;
    height: auto;
    border: ascii white;
    padding: 1;
    }

    #back {
    width: 100%;
    margin: 1 4;
    }
    """

    def compose(self) -> ComposeResult:

        markdown = Markdown(CONTROLS_MARKDOWN)
        markdown.code_indent_guides = False  # ty: ignore[unresolved-attribute]

        with CenterMiddle():
            with Vertical(id="controls_container"):
                with VerticalScroll():
                    yield markdown
                yield Button("Back", id="back")

    def on_mount(self):

        controls_container = self.query_one("#controls_container", Vertical)

        controls_container.border_title = "[bold yellow]Controls[/]"

    def on_button_pressed(self, event: Button.Pressed):

        if event.button.id == "back":
            self.app.pop_screen()

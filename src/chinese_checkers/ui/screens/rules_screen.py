from textual.app import ComposeResult
from textual.containers import CenterMiddle, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Markdown

RULES_MARKDOWN = r"""
> **Objective**
> > Be the first player to race all 10 of your marbles across
> > the hexagram-shaped board into the triangle directly
> > opposite your starting corner.

> **How to Move (Per Turn)**
> > 1. *A Single-Step Move*
> > > Move a marble in any of the six diagonel directions into
> > > an adjacent, empty tile.
> > 2. *A Hopping Move (Jump)*
> > > Hop your marble over a single, immediately adjacent
> > > marble (which can be your own or an opponent's) and
> > > land in the empty space directly on the other side
> > > in a straight line.
> > 3. *No captures*
> > > Unlike traditional checkers, jumped marbles are
> > > not removed from the board.
> > 4. *Multiple Jumps*
> > > You can chain together multiple hops in a single turn
> > > as long as the marble is positioned to make a jump.
> > > You can change directions in the middle of a
> > > hopping chain.

> **Key Rules & Restrictions**
> > 1. *Destination Triangle*
> > > Once a marble enters your target destination triangle,
> > > it cannot be moved out of the triangle for the remainder
> > > of the game, though it can be moved around
> > > within the triangle.
> > 2. *Home Triangle*
> > > Once a marble leaves your home triangle, it cannot
> > > return to the home triangle.
> > 3. *Passing Through*
> > > You are allowed to hop through other opponents'
> > > starting triangles to cross the board, but you
> > > cannot end your turn resting inside them.

"""


class RulesScreen(Screen):
    DEFAULT_CSS = """
    #rules_container {
    width: 75%;
    height: auto;
    border: ascii white;
    padding: 1;
    }

    VerticalScroll {
    width: 100%;
    }

    #back {
    width: 100%;
    margin: 1 4;
    }
    """

    def compose(self) -> ComposeResult:

        markdown = Markdown(RULES_MARKDOWN)
        markdown.code_indent_guides = False  # ty: ignore[unresolved-attribute]

        with CenterMiddle():
            with Vertical(id="rules_container"):
                with VerticalScroll():
                    yield markdown
                yield Button("Back", id="back")

    def on_mount(self):

        rules_container = self.query_one("#rules_container", Vertical)

        rules_container.border_title = "[bold yellow]Rules[/]"

    def on_button_pressed(self, event: Button.Pressed):

        if event.button.id == "back":
            self.app.pop_screen()

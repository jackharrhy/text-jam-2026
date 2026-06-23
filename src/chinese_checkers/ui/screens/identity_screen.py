from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Static
from textual.containers import Vertical, CenterMiddle

import uuid

from chinese_checkers.client.local_identity import save_identity


class IdentityScreen(Screen):
    DEFAULT_CSS = """
    #username_container {
    width: 30;
    height: 11;
    border: ascii white;
    padding: 1;
    }

    Button {
    width: 100%;
    box-sizing: border-box;
    margin: 1 4;
    }
    """

    def compose(self) -> ComposeResult:

        self.name_input = Input(placeholder="Enter your name", id="name")

        with CenterMiddle():
            with Vertical(id="username_container"):
                yield self.name_input
                yield Button("Continue", id="continue")

    def on_mount(self):

        username_container = self.query_one("#username_container", Vertical)

        username_container.border_title = "[bold yellow]Enter Username[/]"

        self.name_input.focus()

    def on_button_pressed(self, event: Button.Pressed):

        if event.button.id != "continue":
            return

        name_input = self.query_one("#name", Input)

        entered_name = name_input.value.strip()

        if not entered_name:
            return

        identity = {
            "player_id": str(uuid.uuid4()),
            "session_id": None,
            "name": entered_name,
        }

        save_identity(identity)

        self.app.client.identity = identity

        self.app.pop_screen()

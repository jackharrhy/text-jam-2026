from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Button, Input
from textual.containers import Vertical, CenterMiddle, Horizontal

from chinese_checkers.client.local_identity import save_identity
from chinese_checkers.ui.screens.lobby_screen import LobbyScreen
from chinese_checkers.shared.settings import PUBLIC_SERVER_HOST, SERVER_PORT
from chinese_checkers.shared.message_types import SESSION_VALIDATED, INVALID_SESSION


class JoinSessionScreen(Screen):
    DEFAULT_CSS = """
    #join_session_container {
    width: 50;
    height: 11;
    border: ascii white;
    padding: 1;
    }

    Horizontal {
    width: 1fr;
    align: center middle;
    }

    Button {
    box-sizing: border-box;
    margin: 1 4;
    }
    """

    def __init__(self):
        super().__init__()

        self.message_handlers = {
            SESSION_VALIDATED: self._handle_session_validated,
            INVALID_SESSION: self._handle_invalid_session,
        }

    def compose(self) -> ComposeResult:

        self.session_id_input = Input(placeholder="Enter session ID", id="session_id")

        with CenterMiddle():
            with Vertical(id="join_session_container"):
                yield self.session_id_input
                with Horizontal():
                    yield Button("Back", id="back")
                    yield Button("Join", id="join_session")

    def on_mount(self):

        join_session_container = self.query_one("#join_session_container", Vertical)

        join_session_container.border_title = "[bold yellow]Join Session[/]"

        self.app.client.on_message = self.handle_message

        self.session_id_input.focus()

    def handle_message(self, data):

        handler = self.message_handlers.get(data["type"])

        if handler:
            handler(data)

    def _handle_session_validated(self, data):

        self.app.call_from_thread(
            self.app.push_screen, LobbyScreen(self.app.client, self.app.client.identity)
        )

    def _handle_invalid_session(self, data):

        identity = self.app.client.identity

        identity["session_id"] = None

        save_identity(identity)

        self.app.call_from_thread(
            self.notify, "Session ID does not exist.", severity="error"
        )

    def on_button_pressed(self, event: Button.Pressed):

        if event.button.id == "join_session":
            session_input = self.query_one("#session_id", Input)

            session_id = session_input.value.strip().upper()

            if not session_id:
                return

            client = self.app.client

            identity = client.identity

            try:
                client.connect_to_session(
                    PUBLIC_SERVER_HOST, SERVER_PORT, identity, session_id=session_id
                )

            except ConnectionRefusedError:
                self.notify("Cannot connect to server.", severity="error")

                return

        elif event.button.id == "back":
            self.app.pop_screen()

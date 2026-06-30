from textual.app import ComposeResult
from textual.containers import CenterMiddle, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input

from chinese_checkers.client.local_identity import save_identity
from chinese_checkers.shared.models import (
    InvalidSessionMessage,
    ServerMessage,
    SessionValidatedMessage,
)
from chinese_checkers.shared.settings import PUBLIC_SERVER_HOST, SERVER_PORT
from chinese_checkers.ui.screens.game_screen import GameScreen
from chinese_checkers.ui.screens.lobby_screen import LobbyScreen


class JoinSessionScreen(Screen):
    DEFAULT_CSS = """
        #join_session_container {
        width: 50;
        height: 13;
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
        self.pending_spectator = False

    def compose(self) -> ComposeResult:

        self.session_id_input = Input(placeholder="Enter session ID", id="session_id")

        with CenterMiddle():
            with Vertical(id="join_session_container"):
                yield self.session_id_input
                with Horizontal():
                    yield Button("Back", id="back")
                    yield Button("Join", id="join_session")
                    yield Button("Spectate", id="spectate_session")

    def on_mount(self):

        join_session_container = self.query_one("#join_session_container", Vertical)

        join_session_container.border_title = "[bold yellow]Join Session[/]"

        self.app.client.on_message = self.handle_message  # ty: ignore[unresolved-attribute]

        self.session_id_input.focus()

    def handle_message(self, msg: ServerMessage):
        if isinstance(msg, SessionValidatedMessage):
            self._handle_session_validated(msg)
        elif isinstance(msg, InvalidSessionMessage):
            self._handle_invalid_session(msg)

    def _handle_session_validated(self, msg):
        if self.pending_spectator:
            if msg.session_state != "in_progress":
                self.app.call_from_thread(
                    self.notify,
                    "Spectators can only join active games.",
                    severity="error",
                )
                return

            self.app.call_from_thread(
                self.app.push_screen,
                GameScreen(
                    self.app.client,  # ty: ignore[unresolved-attribute]
                    self.app.client.identity,  # ty: ignore[unresolved-attribute]
                    None,
                    msg.player_configs,
                ),
            )
            return

        self.app.call_from_thread(
            self.app.push_screen,
            LobbyScreen(self.app.client, self.app.client.identity),  # ty: ignore[unresolved-attribute]
        )

    def _handle_invalid_session(self, _msg):

        identity = self.app.client.identity  # ty: ignore[unresolved-attribute]

        identity.session_id = None

        save_identity(identity)

        self.app.call_from_thread(
            self.notify, "Session ID does not exist.", severity="error"
        )

    def on_button_pressed(self, event: Button.Pressed):

        if event.button.id in {"join_session", "spectate_session"}:
            session_input = self.query_one("#session_id", Input)

            session_id = session_input.value.strip().upper()

            if not session_id:
                return

            client = self.app.client  # ty: ignore[unresolved-attribute]

            identity = client.identity
            self.pending_spectator = event.button.id == "spectate_session"

            try:
                client.connect_to_session(
                    PUBLIC_SERVER_HOST,
                    SERVER_PORT,
                    identity,
                    session_id=session_id,
                    spectator=self.pending_spectator,
                )

            except ConnectionRefusedError:
                self.notify("Cannot connect to server.", severity="error")

                return

        elif event.button.id == "back":
            self.app.pop_screen()

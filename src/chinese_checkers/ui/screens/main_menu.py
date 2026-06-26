from textual.app import ComposeResult
from textual.containers import CenterMiddle, Vertical
from textual.screen import Screen
from textual.widgets import Button

from chinese_checkers.client.local_identity import (
    clear_identity,
    load_identity,
    save_identity,
)
from chinese_checkers.shared.models import (
    DuplicatePlayerMessage,
    ErrorMessage,
    InvalidSessionMessage,
    ServerMessage,
    SessionValidatedMessage,
)
from chinese_checkers.shared.settings import PUBLIC_SERVER_HOST, SERVER_PORT
from chinese_checkers.ui.screens.controls_screen import ControlsScreen
from chinese_checkers.ui.screens.game_screen import GameScreen
from chinese_checkers.ui.screens.identity_screen import IdentityScreen
from chinese_checkers.ui.screens.join_session_screen import JoinSessionScreen
from chinese_checkers.ui.screens.lobby_screen import LobbyScreen
from chinese_checkers.ui.screens.rules_screen import RulesScreen


class MainMenuScreen(Screen):
    DEFAULT_CSS = """
    #menu_container {
    width: 30;
    height: auto;
    border: ascii white;
    padding: 1;
    }

    Button {
    width: auto;
    }

    Vertical {
    align: center middle;
    }

    #change_username {
    dock: bottom;
    width: auto;
    }
    """

    @property
    def _client(self):
        return self.app.client  # ty: ignore[unresolved-attribute]

    def __init__(self):
        super().__init__()

        self._client.on_message = self.handle_message

    def compose(self) -> ComposeResult:

        yield Button("Change Username", id="change_username")

        with CenterMiddle():
            with Vertical(id="menu_container"):
                yield Button("Create Session", id="create")
                yield Button("Join Session", id="join")
                yield Button("Rules", id="rules")
                yield Button("Controls", id="controls")
                yield Button("Quit", id="quit")

    def on_mount(self):

        menu_container = self.query_one("#menu_container", Vertical)

        menu_container.border_title = "[bold yellow]Chinese Checkers[/]"

        self._client.on_message = self.handle_message

        identity = load_identity()

        if identity:
            self._client.identity = identity

            if identity.session_id is not None:
                try:
                    self._client.connect_to_session(
                        PUBLIC_SERVER_HOST,
                        SERVER_PORT,
                        identity,
                        session_id=identity.session_id,
                    )

                except Exception:
                    pass
        else:
            self.app.push_screen(IdentityScreen())

    def handle_message(self, msg: ServerMessage):
        if isinstance(msg, ErrorMessage):
            print(msg.message)

        if isinstance(msg, SessionValidatedMessage):
            self._handle_session_validated(msg)
        elif isinstance(msg, InvalidSessionMessage):
            self._handle_invalid_session(msg)
        elif isinstance(msg, DuplicatePlayerMessage):
            self._handle_duplicate_player(msg)

    def _handle_duplicate_player(self, _msg):

        clear_identity()

        self.app.call_from_thread(self.app.push_screen, IdentityScreen())

    def _handle_invalid_session(self, _msg):
        identity = self._client.identity
        identity.session_id = None
        save_identity(identity)

    def _handle_session_validated(self, msg: SessionValidatedMessage):
        state = msg.session_state

        player_num = msg.player_num
        player_configs = msg.player_configs

        if state == "lobby":
            self.app.call_from_thread(
                self.app.push_screen,
                LobbyScreen(self._client, self._client.identity),
            )

        elif state == "in_progress":
            self.app.call_from_thread(
                self.app.push_screen,
                GameScreen(
                    self._client,
                    self._client.identity,
                    player_num,
                    player_configs,
                ),
            )

    def on_button_pressed(self, event: Button.Pressed):

        button_id = event.button.id

        if button_id == "quit":
            self.app.exit()

        elif button_id == "create":
            self.create_session(2)

        elif button_id == "join":
            identity = self._client.identity

            if not identity:
                self.app.push_screen(IdentityScreen())
                return

            self.app.push_screen(JoinSessionScreen())

        elif button_id == "change_username":
            clear_identity()

            self._client.identity = None

            self.app.push_screen(IdentityScreen())

        elif button_id == "rules":
            self.app.push_screen(RulesScreen())

        elif button_id == "controls":
            self.app.push_screen(ControlsScreen())

    def create_session(self, num_players):

        client = self._client
        identity = client.identity

        if not identity:
            self.app.push_screen(IdentityScreen())
            return

        try:
            client.connect_to_session(
                PUBLIC_SERVER_HOST,
                SERVER_PORT,
                identity,
                session_id=None,
                num_players=num_players,
            )

        except ConnectionRefusedError:
            self.notify("Cannot connect to server.", severity="error")

            return

        self.app.push_screen(LobbyScreen(client, identity))

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Button
from textual.containers import Vertical, CenterMiddle

from chinese_checkers.ui.screens.game_screen import GameScreen
from chinese_checkers.ui.screens.lobby_screen import LobbyScreen
from chinese_checkers.ui.screens.identity_screen import IdentityScreen
from chinese_checkers.ui.screens.rules_screen import RulesScreen
from chinese_checkers.ui.screens.controls_screen import ControlsScreen
from chinese_checkers.ui.screens.join_session_screen import JoinSessionScreen
from chinese_checkers.client.local_identity import (
    save_identity,
    load_identity,
    clear_identity,
)
from chinese_checkers.shared.message_types import (
    ERROR,
    SESSION_VALIDATED,
    INVALID_SESSION,
    DUPLICATE_PLAYER,
)
from chinese_checkers.shared.settings import PUBLIC_SERVER_HOST, SERVER_PORT


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

    def __init__(self):
        super().__init__()

        self.app.client.on_message = self.handle_message

        self.message_handlers = {
            SESSION_VALIDATED: self._handle_session_validated,
            INVALID_SESSION: self._handle_invalid_session,
            DUPLICATE_PLAYER: self._handle_duplicate_player,
        }

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

        self.app.client.on_message = self.handle_message

        identity = load_identity()

        if identity:
            self.app.client.identity = identity

            if identity["session_id"] is not None:
                try:
                    self.app.client.connect_to_session(
                        PUBLIC_SERVER_HOST,
                        SERVER_PORT,
                        identity,
                        session_id=identity["session_id"],
                    )

                except Exception:
                    pass
        else:
            self.app.push_screen(IdentityScreen())

    def handle_message(self, data):
        if data["type"] == ERROR:
            print(data["message"])

        handler = self.message_handlers.get(data["type"])

        if handler:
            handler(data)

    def _handle_duplicate_player(self, data):

        clear_identity()

        self.app.call_from_thread(self.app.push_screen, IdentityScreen())

    def _handle_invalid_session(self, data):
        identity = self.app.client.identity
        identity["session_id"] = None
        save_identity(identity)

    def _handle_session_validated(self, data):
        state = data["session_state"]

        player_num = data["player_num"]
        player_configs = data["player_configs"]

        if state == "lobby":
            self.app.call_from_thread(
                self.app.push_screen,
                LobbyScreen(self.app.client, self.app.client.identity),
            )

        elif state == "in_progress":
            self.app.call_from_thread(
                self.app.push_screen,
                GameScreen(
                    self.app.client,
                    self.app.client.identity,
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
            identity = self.app.client.identity

            if not identity:
                self.app.push_screen(IdentityScreen())
                return

            self.app.push_screen(JoinSessionScreen())

        elif button_id == "change_username":
            clear_identity()

            self.app.client.identity = None

            self.app.push_screen(IdentityScreen())

        elif button_id == "rules":
            self.app.push_screen(RulesScreen())

        elif button_id == "controls":
            self.app.push_screen(ControlsScreen())

    def create_session(self, num_players):

        client = self.app.client
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

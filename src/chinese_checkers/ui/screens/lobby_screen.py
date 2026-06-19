from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, Button, Select, RichLog, Input
from textual.containers import Vertical, Horizontal, CenterMiddle

from chinese_checkers.client.local_identity import save_identity
from chinese_checkers.ui.screens.game_screen import GameScreen
from chinese_checkers.shared.message_types import (
    WELCOME,
    LOBBY_STATE,
    GAME_STARTED,
    START_GAME,
    UPDATE_NUM_PLAYERS,
    LEAVE_LOBBY,
    KICK_PLAYER,
    KICKED_FROM_LOBBY,
    CHAT,
)


class LobbyScreen(Screen):
    DEFAULT_CSS = """
    #player_list {
    padding-top: 1;
    height: auto;
    }
    
    #main_lobby_container {
    border: ascii white;
    }
    #lobby_chat_container {
    border: ascii white;
    }

    #lobby_button_container {
    align: center bottom;

    
    #chat_input {
    
    }

    }
    """

    def __init__(self, client, identity):

        super().__init__()

        self.client = client
        self.identity = identity

        self.player_number = None
        self.is_host = False

        self.session_id = None
        self.players = []
        self.num_players = None
        self.player_configs = None

        self.client.on_message = self.handle_message
        self.client.on_disconnect = self.handle_disconnect
        self.client.log_message = self.log_message

        self.message_handlers = {
            WELCOME: self._handle_welcome,
            GAME_STARTED: self._handle_game_started,
            LOBBY_STATE: self._handle_lobby_state,
            KICKED_FROM_LOBBY: self._handle_kicked_from_lobby,
            CHAT: self._handle_chat,
        }

    def compose(self) -> ComposeResult:

        self.session_id_widget = Static()
        self.player_count_select = Select(
            [
                ("2 Players", 2),
                ("3 Players", 3),
                ("4 Players", 4),
                ("6 Players", 6),
            ],
            value=2,
            prompt="Select number of players",
            id="player_count",
        )
        self.players_widget = Vertical(id="player_list")
        self.status_widget = Static()
        self.start_button = Button("Start Game", id="start_game")
        self.back_button = Button("Leave Lobby", id="leave_lobby")

        self.message_log = RichLog(
            highlight=True, markup=True, wrap=True, id="lobby_chat_container"
        )

        self.chat_input = Input(placeholder="Say something...", id="chat_input")

        with CenterMiddle():
            with Horizontal(id="main_lobby_container"):
                with Vertical():
                    yield self.session_id_widget
                    yield self.player_count_select
                    yield self.status_widget
                    yield self.players_widget
                    with Horizontal(id="lobby_button_container"):
                        yield self.back_button
                        yield self.start_button
                with Vertical():
                    yield self.message_log
                    yield self.chat_input

    def on_mount(self):

        main_lobby_container = self.query_one("#main_lobby_container", Horizontal)
        main_lobby_container.border_title = "[bold yellow]Lobby[/]"

        lobby_chat_container = self.query_one("#lobby_chat_container", RichLog)
        lobby_chat_container.border_title = "[bold]Chat[/]"

        if self.session_id and self.players:
            self.refresh_lobby()

    def log_message(self, message):

        self.message_log.write(message)

    def refresh_lobby(self):

        self.session_id_widget.update(f"Session ID: [bold]{self.session_id}[/]")

        if self.num_players is not None:
            self.player_count_select.value = self.num_players

        self.call_after_refresh(self.rebuild_player_list)

        # Update status
        connected_players = sum(1 for player in self.players if player["connected"])

        all_connected = all(player["connected"] for player in self.players)

        if connected_players == self.num_players and all_connected:
            if self.is_host:
                status_message = "[bold green]Ready to start game[/]"
            else:
                status_message = "[bold green]Waiting for host to start game[/]"
        elif connected_players < self.num_players or not all_connected:
            status_message = "[bold yellow]Waiting for players...[/]"
        elif connected_players > self.num_players:
            status_message = "[bold red]Too many players...[/]"
        self.status_widget.update(status_message)

        # Update dropdown if player has become the new host
        if self.is_host and self.player_count_select.disabled:
            self.player_count_select.disabled = False

        # Update start button
        can_start = (
            self.is_host and connected_players == self.num_players and all_connected
        )

        self.start_button.disabled = not can_start

    def rebuild_player_list(self):

        self.players_widget.remove_children()
        self.players_widget.refresh(layout=True)

        for player in self.players:
            self.players_widget.mount(
                PlayerRow(player, self.is_host, self.identity["player_id"])
            )

    def handle_disconnect(self):

        self.status_widget.update("[bold red]Connection to server lost.[/]")

    def handle_message(self, data):

        handler = self.message_handlers.get(data["type"])

        if handler:
            handler(data)

    def _handle_chat(self, data):
        text = f"[cyan]{data['player_name']}:[/] {data['message']}"
        self.client.dispatch_to_ui(self.app, self.log_message, text)

    def _handle_kicked_from_lobby(self, data):

        self.client.dispatch_to_ui(self.app, self._process_kick)

    def _process_kick(self):
        # def _handle_kicked_from_lobby(self, data):

        # Clear lobby state
        self.session_id = None
        self.players = []
        self.num_players = None
        self.is_host = False

        # Remove stored session
        self.identity["session_id"] = None
        save_identity(self.identity)

        # Clear widgets
        self.session_id_widget.update("[bold red]Not in a lobby[/]")
        self.players_widget.remove_children()
        self.status_widget.update("")

        # Show toast
        self.notify("You were kicked from the lobby.", severity="warning")

        self.client.close()

        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

    def _handle_welcome(self, data):

        self.session_id = data["session_id"]

        self.identity["player_id"] = data.get("player_id")

        self.identity["session_id"] = data["session_id"]

        save_identity(self.identity)

        self.player_number = data["player_number"]

        # Only host can start the game
        if not self.is_host:
            self.start_button.disabled = True
            self.player_count_select.disabled = True

        self.player_configs = data["players"]

        self.client.dispatch_to_ui(self.app, self.refresh_lobby)

    def _handle_game_started(self, data):

        self.player_number = data["player_number"]

        self.player_configs = data["player_configs"]

        self.client.dispatch_to_ui(self.app, self._enter_game_screen)

    def _handle_lobby_state(self, data):

        self.session_id = data["session_id"]

        self.players = data["players"]

        self.num_players = data["num_players"]

        self.is_host = data["is_host"]

        self.client.dispatch_to_ui(self.app, self.refresh_lobby)

    def _enter_game_screen(self):

        self.client.send(
            {
                "type": "debug",
                "message": f"Lobby Screen: _enter_game_screen: {self.player_number}",
            }
        )

        self.app.push_screen(
            GameScreen(
                self.client, self.identity, self.player_number, self.player_configs
            )
        )

    def on_button_pressed(self, event):

        if event.button.id == "start_game":
            self.client.send({"type": START_GAME})

        if event.button.id.startswith("kick_"):
            player_id = event.button.id.removeprefix("kick_")

            self.client.send({"type": KICK_PLAYER, "player_id": player_id})

            return

        if event.button.id == "leave_lobby":
            self.client.send({"type": LEAVE_LOBBY})

            self.identity["session_id"] = None

            save_identity(self.identity)

            self.client.close()

            while len(self.app.screen_stack) > 2:
                self.app.pop_screen()

    def on_select_changed(self, event: Select.Changed):

        if event.select.id == "player_count":
            if event.value is Select.NULL:
                return

            self.client.send({"type": UPDATE_NUM_PLAYERS, "num_players": event.value})

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat_input":
            self.client.send({"type": CHAT, "message": event.value})
            event.input.value = ""


class PlayerRow(Horizontal):
    DEFAULT_CSS = """
    PlayerRow {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    #player_label {
        width: auto;
    }

    .kick-button {
        width: 6;
        min-width: 6;
        align: right middle;
        dock: right;
    }
    """

    def __init__(self, player, is_host_user, current_player_id):
        super().__init__()

        self.player = player
        self.is_host_user = is_host_user
        self.current_player_id = current_player_id

    def compose(self):

        label = Static(self.name_text(), id="player_label")

        yield label

        if self.show_kick():
            yield Button(
                "Kick",
                id=f"kick_{self.player['player_id']}",
                classes="kick-button",
                compact=True,
            )

    def name_text(self):
        name = self.player["name"]
        if self.player["connected"]:
            name += " [green](connected)[/]"
        else:
            name += " [red](disconnected)[/]"
        if self.player["is_host"]:
            name += " [grey](host)[/]"

        return name

    def show_kick(self):
        return self.is_host_user and self.player["player_id"] != self.current_player_id

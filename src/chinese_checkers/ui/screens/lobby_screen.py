from textual.app import ComposeResult
from textual.containers import CenterMiddle, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, RichLog, Select, Static


from chinese_checkers.client.local_identity import save_identity
from chinese_checkers.shared.models import (
    ClientChatMessage,
    DebugMessage,
    GameStartedMessage,
    Identity,
    KickedFromLobbyMessage,
    KickPlayerMessage,
    LeaveLobbyMessage,
    LobbyPlayer,
    LobbyStateMessage,
    PlayerConfig,
    ServerChatMessage,
    ServerMessage,
    StartGameMessage,
    UpdateNumPlayersMessage,
    WelcomeMessage,
)
from chinese_checkers.ui.screens.game_screen import GameScreen


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
        self.identity = Identity(**identity) if isinstance(identity, dict) else identity

        self.player_number = None
        self.is_host = False

        self.session_id = None
        self.players: list[LobbyPlayer] = []
        self.num_players = None
        self.cpu_count = 0
        self.player_configs: list[PlayerConfig] | None = None

        self.client.on_message = self.handle_message
        self.client.on_disconnect = self.handle_disconnect
        self.client.log_message = self.log_message

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

        self.cpu_count_select = Select(
            [
                ("0 CPUs", 0),
                ("1 CPU", 1),
                ("2 CPUs", 2),
                ("3 CPUs", 3),
                ("4 CPUs", 4),
                ("5 CPUs", 5),
            ],
            value=0,
            prompt="Number of CPUs",
            id="cpu_count",
        )

        with CenterMiddle():
            with Horizontal(id="main_lobby_container"):
                with Vertical():
                    yield self.session_id_widget
                    yield self.player_count_select
                    yield self.cpu_count_select
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

        if self.num_players is None:
            return

        self.session_id_widget.update(f"Session ID: [bold]{self.session_id}[/]")

        self.call_after_refresh(self.rebuild_player_list)

        connected_players = sum(1 for player in self.players if player.connected)

        all_connected = all(player.connected for player in self.players)

        cpu = min(self.cpu_count or 0, self.num_players - connected_players)
        total_players = connected_players + cpu

        if total_players == self.num_players and all_connected:
            if self.is_host:
                status_message = "[bold green]Ready to start game[/]"
            else:
                status_message = "[bold green]Waiting for host to start game[/]"
        elif connected_players < (self.num_players - cpu) or not all_connected:
            status_message = "[bold yellow]Waiting for players...[/]"
        elif connected_players > (self.num_players - cpu):
            status_message = "[bold red]Too many players...[/]"
        else:
            status_message = ""
        self.status_widget.update(status_message)

        if self.is_host:
            if self.player_count_select.disabled:
                self.player_count_select.disabled = False
            if self.cpu_count_select.disabled:
                self.cpu_count_select.disabled = False

        can_start = (
            self.is_host
            and total_players == self.num_players
            and all_connected
        )

        self.start_button.disabled = not can_start

    def rebuild_player_list(self):

        self.players_widget.remove_children()
        self.players_widget.refresh(layout=True)

        for player in self.players:
            self.players_widget.mount(
                PlayerRow(player, self.is_host, self.identity.player_id)
            )

    def handle_disconnect(self):

        self.status_widget.update("[bold red]Connection to server lost.[/]")

    def handle_message(self, msg: ServerMessage):

        if isinstance(msg, WelcomeMessage):
            self._handle_welcome(msg)
        elif isinstance(msg, GameStartedMessage):
            self._handle_game_started(msg)
        elif isinstance(msg, LobbyStateMessage):
            self._handle_lobby_state(msg)
        elif isinstance(msg, KickedFromLobbyMessage):
            self._handle_kicked_from_lobby(msg)
        elif isinstance(msg, ServerChatMessage):
            self._handle_chat(msg)

    def _handle_chat(self, msg: ServerChatMessage):
        text = f"[cyan]{msg.player_name}:[/] {msg.message}"
        self.client.dispatch_to_ui(self.app, self.log_message, text)

    def _handle_kicked_from_lobby(self, msg: KickedFromLobbyMessage):

        self.client.dispatch_to_ui(self.app, self._process_kick)

    def _process_kick(self):
        # def _handle_kicked_from_lobby(self, data):

        # Clear lobby state
        self.session_id = None
        self.players = []
        self.num_players = None
        self.is_host = False

        # Remove stored session
        self.identity.session_id = None
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

    def _handle_welcome(self, msg: WelcomeMessage):

        self.session_id = msg.session_id

        self.identity.player_id = msg.player_id

        self.identity.session_id = msg.session_id

        save_identity(self.identity)

        self.player_number = msg.player_number

        # Only host can start the game
        if not self.is_host:
            self.start_button.disabled = True
            self.player_count_select.disabled = True
            self.cpu_count_select.disabled = True

        self.player_configs = msg.players

        self.client.dispatch_to_ui(self.app, self.refresh_lobby)

    def _handle_game_started(self, msg: GameStartedMessage):

        self.player_number = msg.player_number

        self.player_configs = msg.player_configs

        self.client.dispatch_to_ui(self.app, self._enter_game_screen)

    def _handle_lobby_state(self, msg: LobbyStateMessage):

        self.session_id = msg.session_id

        self.players = msg.players

        self.num_players = msg.num_players

        self.is_host = msg.is_host

        if not self.is_host:
            self.player_count_select.value = msg.num_players

        self.client.dispatch_to_ui(self.app, self.refresh_lobby)

    def _enter_game_screen(self):

        self.client.send(
            DebugMessage(
                message=f"Lobby Screen: _enter_game_screen: {self.player_number}"
            )
        )

        self.app.push_screen(
            GameScreen(
                self.client, self.identity, self.player_number, self.player_configs
            )
        )

    def on_button_pressed(self, event):

        if event.button.id == "start_game":
            self.client.send(StartGameMessage(cpu_count=self.cpu_count or 0))

        if event.button.id.startswith("kick_"):
            player_id = event.button.id.removeprefix("kick_")

            self.client.send(KickPlayerMessage(player_id=player_id))

            return

        if event.button.id == "leave_lobby":
            self.client.send(LeaveLobbyMessage())

            self.identity.session_id = None

            save_identity(self.identity)

            self.client.close()

            while len(self.app.screen_stack) > 2:
                self.app.pop_screen()

    def on_select_changed(self, event: Select.Changed):

        if event.select.id == "player_count":
            if event.value is Select.NULL:
                return

            assert isinstance(event.value, int)
            self.client.send(UpdateNumPlayersMessage(num_players=event.value))

        elif event.select.id == "cpu_count":
            if event.value is Select.NULL:
                return

            assert isinstance(event.value, int)
            self.cpu_count = event.value
            self.refresh_lobby()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat_input":
            self.client.send(ClientChatMessage(message=event.value))
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

    def __init__(self, player: LobbyPlayer, is_host_user, current_player_id):
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
                id=f"kick_{self.player.player_id}",
                classes="kick-button",
                compact=True,
            )

    def name_text(self):
        name = self.player.name
        if self.player.is_cpu:
            name += " [grey][CPU][/]"
        elif self.player.connected:
            name += " [green](connected)[/]"
        else:
            name += " [red](disconnected)[/]"
        if self.player.is_host:
            name += " [grey](host)[/]"

        return name

    def show_kick(self):
        return self.is_host_user and self.player.player_id != self.current_player_id

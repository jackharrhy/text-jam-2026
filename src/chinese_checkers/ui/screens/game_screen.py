from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen

from textual.widgets import Button, Input, RichLog, Static

from chinese_checkers.shared.models import (
    ClientChatMessage,
    ErrorMessage,
    GameStateMessage,
    LeaveGameMessage,
    MoveMessage,
    PartialValidationMessage,
    PlayerDisconnectedMessage,
    PlayerJoinedGameMessage,
    PlayerQuitMessage,
    PlayerReconnectedMessage,
    ServerChatMessage,
    ServerMessage,
    ValidatePartialMessage,
)
from chinese_checkers.ui.board_layout import ZONE_CURSOR_STARTS
from chinese_checkers.ui.board_renderer import BoardRenderer
from chinese_checkers.ui.geometry import DIRECTIONS
from chinese_checkers.ui.screens.controls_screen import ControlsScreen
from chinese_checkers.ui.screens.rules_screen import RulesScreen


class GameScreen(Screen):
    BINDINGS = [
        ("tab", "cycle_piece", "Cycle Piece"),
        ("/", "focus_chat", "Chat"),
    ]

    DEFAULT_CSS = """
    #game_screen_container {
    border: ascii white;
    height: 100%;
    }

    #game_area {
    height: 1fr;
    layout: vertical;
    }

    #board_container {
        height: 1fr;
        align: center middle;
    }

    #game_board {
        width: 50%;
        min-width: 25;
        height: auto;
    }

    #button_bar {
        height: auto;
        dock: bottom;
        align: center bottom;
        width: 100%;
    }

    #button_bar Button {
    width: 30%;
    min-width: 10;
    box-sizing: border-box;
    margin: 1 2;
    }

    #game_chat {
    border: ascii white;
    }
    """

    def __init__(self, client, identity, player_number=None, player_configs=None):

        super().__init__()

        self.client = client
        self.identity = identity

        self.renderer = BoardRenderer()

        self.board = {}

        self.player_number = player_number
        self.player_configs = player_configs

        self.my_turn = False
        self.selected_path = []

        self.cursor = None
        self.tick = 0

        self.client.on_message = self.handle_message
        self.client.on_disconnect = self.handle_disconnect
        self.client.log_message = self.log_message

    def compose(self) -> ComposeResult:

        self.board_widget = Static(id="game_board")

        self.message_log = RichLog(
            highlight=True, markup=True, wrap=True, id="game_chat"
        )
        self.message_log.can_focus = False

        rules_button = Button("Rules", id="rules", compact=True)
        rules_button.can_focus = False

        controls_button = Button("Controls", id="controls", compact=True)
        controls_button.can_focus = False

        quit_button = Button("Quit", id="quit_game", compact=True)
        quit_button.can_focus = False

        self.chat_input = Input(placeholder="Say something...", id="chat_input")

        with Horizontal(id="game_screen_container"):
            with Vertical(id="game_area"):
                with Vertical(id="board_container"):
                    yield self.board_widget
                with Horizontal(id="button_bar"):
                    yield rules_button
                    yield controls_button
                    yield quit_button

            with Vertical(id="chat_area"):
                yield self.message_log
                yield self.chat_input

    def on_mount(self):

        game_screen_container = self.query_one("#game_screen_container", Horizontal)
        game_screen_container.border_title = (
            f"[bold yellow]Session ID: {self.identity.session_id}[/]"
        )

        game_chat = self.query_one("#game_chat", RichLog)
        game_chat.border_title = "[bold]Chat[/]"

        self.refresh_board()

        self.set_interval(0.08, self.animate_cursor)

        if not self.player_configs:
            return

        player_config = next(
            (
                config
                for config in self.player_configs
                if config.player == self.player_number
            ),
            None,
        )

        if player_config is None:
            return

        start_zone = player_config.start

        self.cursor = ZONE_CURSOR_STARTS[start_zone]

    def animate_cursor(self):

        self.tick += 1

        self.refresh_board()

    def handle_disconnect(self):

        self.my_turn = False
        self.selected_path.clear()
        self.cursor = None

        self.log_message("[bold red]Connection to server lost...[/]")

    def handle_message(self, msg: ServerMessage):

        if isinstance(msg, GameStateMessage):
            self._handle_game_state(msg)
        elif isinstance(msg, PartialValidationMessage):
            self._handle_partial_validation(msg)
        elif isinstance(msg, ErrorMessage):
            self._handle_error(msg)
        elif isinstance(msg, PlayerReconnectedMessage):
            self._handle_player_reconnect(msg)
        elif isinstance(msg, PlayerDisconnectedMessage):
            self._handle_player_disconnect(msg)
        elif isinstance(msg, PlayerJoinedGameMessage):
            self._handle_player_joined_game(msg)
        elif isinstance(msg, PlayerQuitMessage):
            self._handle_player_quit(msg)
        elif isinstance(msg, ServerChatMessage):
            self._handle_chat(msg)

    def _handle_chat(self, msg: ServerChatMessage):

        player_style = self.get_player_style(msg.player_number)

        message = Text(f"{msg.player_name}", style=player_style)

        message.append(": ", style="white")
        message.append(msg.message, style="white")

        self.client.dispatch_to_ui(self.app, self.log_message, message)

    def get_player_style(self, player_number):

        if self.player_configs is None:
            return "cyan"

        config = next(
            (
                config
                for config in self.player_configs
                if config.player == player_number
            ),
            None,
        )

        return str(config.piece) if config else "cyan"

    def _handle_game_state(self, msg: GameStateMessage):

        serialized_board = msg.board

        new_board = {}
        for key, value in serialized_board.items():
            q, r = map(int, key.split(","))
            new_board[(q, r)] = value

        self.client.dispatch_to_ui(
            self.app, self.update_game_state, new_board, msg.current_player, msg.winner
        )

    def _handle_partial_validation(self, msg: PartialValidationMessage):

        self.client.dispatch_to_ui(
            self.app,
            self.handle_partial_validation,
            msg.valid,
            msg.message,
            self.cursor,
        )

    def _handle_error(self, msg: ErrorMessage):

        self.client.dispatch_to_ui(self.app, self.show_error, msg.message)

    def _handle_player_reconnect(self, msg: PlayerReconnectedMessage):

        player_name = msg.player_name

        self.client.dispatch_to_ui(
            self.app,
            self.log_message,
            f"[green]{player_name} reconnected to the game.[/]",
        )

    def _handle_player_disconnect(self, msg: PlayerDisconnectedMessage):

        player_name = msg.player_name

        self.client.dispatch_to_ui(
            self.app,
            self.log_message,
            f"[green]{player_name} disconnected from the game.[/]",
        )

    def _handle_player_quit(self, msg: PlayerQuitMessage):

        player_name = msg.player_name

        self.client.dispatch_to_ui(
            self.app, self.log_message, f"[green]{player_name} quit the game.[/]"
        )

    def _handle_player_joined_game(self, msg: PlayerJoinedGameMessage):

        self.client.dispatch_to_ui(
            self.app, self.show_player_joined, msg.player_name, msg.player_number
        )

    def show_player_joined(self, player_name, player_number):

        player_style = self.get_player_style(player_number)

        message = Text(player_name, style=player_style)

        message.append(" has joined the game!", style="white")
        self.message_log.write(message)

    def update_game_state(self, new_board, current_player, winner):

        self.board = new_board

        if not self.player_configs:
            return

        # -----------------
        # Handle game over
        # -----------------

        if winner is not None:
            self.my_turn = False

            if winner == self.player_number:
                self.log_message("[bold green]You win![/]")

            else:
                self.log_message(f"[bold red]Player {winner} wins.[/]")

            self.refresh_board()

            return

        # ------------
        # Normal turn
        # ------------

        was_my_turn = self.my_turn

        self.my_turn = current_player == self.player_number

        if self.my_turn and not was_my_turn:
            self.log_message("[bold yellow]Your turn![/]")

        if not self.my_turn and winner is None:
            if not hasattr(self, "_was_waiting") or not self._was_waiting:
                self.log_message("[cyan]Waiting for opponent...[/]")
                self._was_waiting = True
        else:
            self._was_waiting = False

        self.refresh_board()

    def show_error(self, message):

        self.notify(f"[bold yellow]Invalid move:[/] {message}", severity="error")

    def refresh_board(self):

        visible_cursor = self.cursor if self.my_turn else None

        board_text = self.renderer.build_board_text(
            self.board,
            self.player_configs,
            visible_cursor,
            self.selected_path,
            self.tick,
        )

        self.board_widget.update(board_text)

    def action_cycle_piece(self):

        if self.my_turn:
            self.cycle_to_next_piece()

    def cycle_to_next_piece(self):

        # Only allow cycling before selecting a piece
        if self.selected_path:
            return

        player_pieces = sorted(
            [
                coord
                for coord, occupant in self.board.items()
                if occupant == self.player_number
            ],
            key=lambda coord: (coord[1], coord[0]),
        )

        if not player_pieces:
            return

        # If cursor isn't on one of the player's pieces,
        # jump to the first one
        if self.cursor not in player_pieces:
            self.cursor = player_pieces[0]

            self.refresh_board()

            return

        current_index = player_pieces.index(self.cursor)

        next_index = (current_index + 1) % len(player_pieces)

        self.cursor = player_pieces[next_index]

        self.refresh_board()

    def action_focus_chat(self):
        self.set_focus(self.chat_input)

    def on_click(self, event):
        chat_input = self.query_one("#chat_input")

        if event.widget != chat_input:
            self.app.set_focus(None)

    def on_key(self, event: Key):

        key = event.key.lower()
        if (
            key == "escape"
            and self.app.focused is not None
            and self.app.focused.id == "chat_input"
        ):
            self.app.set_focus(None)

        if not self.my_turn:
            return

        if key in DIRECTIONS:
            if self.cursor is None:
                return

            direction = DIRECTIONS[key]

            new_coord = (self.cursor[0] + direction[0], self.cursor[1] + direction[1])

            if new_coord in self.board:
                self.cursor = new_coord

                self.refresh_board()

        elif key == "space":
            proposed_path = self.selected_path + [self.cursor]

            self.client.send(ValidatePartialMessage(path=proposed_path))

        elif key == "enter":
            if self.app.focused != None and self.app.focused.id == "chat_input":
                return

            if len(self.selected_path) >= 2:
                self.send_move()

                self.selected_path.clear()

                self.refresh_board()

            elif len(self.selected_path) == 1:
                self.notify(
                    "[bold yellow]Invalid move:[/] Select a tile to move to.",
                    severity="error",
                )

            else:
                self.notify(
                    "[bold yellow]Invalid move:[/] Select a piece to move.",
                    severity="error",
                )

        elif (
            key == "escape"
            and self.app.focused is not None
            and self.app.focused.id == "chat_input"
        ):
            self.app.set_focus(None)

        elif key == "escape" and self.selected_path:
            self.cursor = self.selected_path[-1]

            self.selected_path.pop()

            self.refresh_board()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat_input":
            self.client.send(ClientChatMessage(message=event.value))
            event.input.value = ""

    def send_move(self):

        self.client.send(MoveMessage(path=self.selected_path))

    def handle_partial_validation(self, valid, message, coord):

        if valid:
            self.selected_path.append(coord)

            self.refresh_board()

        else:
            self.show_error(message)

    def log_message(self, message):

        self.message_log.write(message)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "quit_game":
            self.quit_game()
        if event.button.id == "rules":
            self.app.push_screen(RulesScreen())
        if event.button.id == "controls":
            self.app.push_screen(ControlsScreen())

    def quit_game(self):

        self.client.send(LeaveGameMessage())

        self.my_turn = False

        try:
            self.client.close()
        except:
            pass

        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

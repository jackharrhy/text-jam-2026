import random
import threading
import time
import uuid
from pathlib import Path

from chinese_checkers.game.cpu_brain import generate_move
from chinese_checkers.game.game_state import GameState
from chinese_checkers.game.move_validator import validate_move, validate_partial_move
from chinese_checkers.game.player import Player
from chinese_checkers.server.session_states import IN_PROGRESS, LOBBY
from chinese_checkers.shared.models import (
    ClientChatMessage,
    ClientMessage,
    ErrorMessage,
    GameStartedMessage,
    GameStateMessage,
    KickedFromLobbyMessage,
    KickPlayerMessage,
    LobbyPlayer,
    LobbyStateMessage,
    MoveMessage,
    PartialValidationMessage,
    PlayerDisconnectedMessage,
    PlayerJoinedGameMessage,
    PlayerQuitMessage,
    PlayerReconnectedMessage,
    ServerChatMessage,
    ServerMessage,
    StartGameMessage,
    UpdateNumPlayersMessage,
    ValidatePartialMessage,
    WelcomeMessage,
)
from chinese_checkers.shared.network import safe_send_message, send_message

RECONNECT_TIMEOUT = 300  # Clean up session after five minutes of inactivity.

CPU_NAMES = (
    Path(__file__).parents[1] / "game" / "cpu_names.txt"
).read_text().strip().splitlines()


class Session:
    def __init__(self, session_id, num_players, cpu_count=0):
        self.session_id = session_id

        self.lobby_num_players = num_players
        self.cpu_count = cpu_count
        self.game_num_players = None

        self.players: dict = {}

        self.host_player_id = None

        self.game_state = None

        self.lock = threading.Lock()

        self.state = LOBBY

        self.chat_history: list[ServerChatMessage] = []

        self.created_at = time.time()
        self.last_activity = time.time()

    def add_player(self, player):

        self.touch()

        if not self.host_player_id:
            self.host_player_id = player.player_id

        self.players[player.player_id] = player

        for msg in self.chat_history:
            safe_send_message(player, msg)

        self.broadcast_session_state()

        return True

    def remove_player(self, player):

        if player.player_id not in self.players:
            return

        was_host = player.player_id == self.host_player_id

        del self.players[player.player_id]

        if was_host:
            self.host_player_id = None

            self.assign_new_host()

        self.broadcast_session_state()

        print(f"Player {player.player_id} left session {self.session_id}")

    def assign_new_host(self):

        print("assigning new host...")

        for player in self.players.values():
            if player.connected:
                self.host_player_id = player.player_id
                return

        self.host_player_id = None

    def assign_player_numbers(self):
        for i, player in enumerate(self.players.values(), start=1):
            player.player_number = i

    def get_connected_players(self):

        return [
            player.player_id for player in self.players.values() if player.connected
        ]

    def get_player_num(self, player_id):

        for player in self.players.values():
            if player.player_id == player_id:
                return player.player_number

        return None

    def serialize_players(self) -> list[LobbyPlayer]:

        return [
            LobbyPlayer(
                player_id=player.player_id,
                name=player.name,
                player_number=player.player_number,
                connected=player.connected,
                is_host=player.player_id == self.host_player_id,
                is_cpu=player.is_cpu,
            )
            for player in self.players.values()
        ]

    def handle_reconnect(self, player):

        self.broadcast_session_state()

        if self.host_player_id is None:
            self.host_player_id = player.player_id

        for msg in self.chat_history:
            safe_send_message(player, msg)

        if self.state == LOBBY:
            safe_send_message(player, WelcomeMessage.for_player(player, self))

        elif self.state == IN_PROGRESS:
            self.broadcast_to_game(
                PlayerReconnectedMessage(
                    player_name=player.name,
                    player_number=player.player_number,
                )
            )

    def handle_disconnect(self, player):

        if not player.connected:
            return

        if player.player_id not in self.players:
            return

        player.disconnect()

        if self.state == LOBBY and player.player_id == self.host_player_id:
            self.assign_new_host()

        if self.state == IN_PROGRESS:
            self.broadcast_to_game(
                PlayerDisconnectedMessage(
                    player_name=player.name,
                    player_number=player.player_number,
                )
            )

        self.broadcast_session_state()

        print(
            f"Session.py: handle_disconnect(): Player {player.player_number} disconnected "
            f"from session {self.session_id}"
        )

    def all_players_connected(self):

        return all(
            player.connected or player.is_cpu
            for player in self.players.values()
        )

    def touch(self):

        self.last_activity = time.time()

    def is_abandoned(self):

        now = time.time()

        for player in self.players.values():
            if player.connected:
                return False

            if now - player.last_seen < RECONNECT_TIMEOUT:
                return False

        return True

    def broadcast_to_game(self, message: ServerMessage):
        if self.state != IN_PROGRESS:
            return

        for player in self.players.values():
            if player.connection:
                safe_send_message(player, message)

    def broadcast_session_state(self):

        if self.state is LOBBY:
            self.broadcast_lobby_state()
        elif self.state is IN_PROGRESS:
            self.broadcast_game_state()

    def broadcast_lobby_state(self):

        print("broadcasting lobby state")
        for player in self.players.values():
            if player.connected and player.connection:
                safe_send_message(player, LobbyStateMessage.for_player(self, player))

    def broadcast_game_state(self):

        print("broadcasting game state")
        for player in self.players.values():
            if player.connected and player.connection:
                safe_send_message(
                    player,
                    GameStateMessage.from_game_state(self.game_state),
                )

    def start_game(self):

        # Fill remaining slots with CPU players
        human_count = len(self.players)
        cpu_needed = min(
            self.cpu_count,
            self.lobby_num_players - human_count,
        )
        for i in range(cpu_needed):
            cpu_name = random.choice(CPU_NAMES)
            cpu_player = Player(
                player_id=str(uuid.uuid4()),
                name=f"{cpu_name} [CPU]",
                session_id=self.session_id,
                is_cpu=True,
            )
            cpu_player.connected = True
            self.players[cpu_player.player_id] = cpu_player

        self.game_num_players = len(self.players)

        self.assign_player_numbers()

        print("START GAME: ", self.game_num_players)

        self.game_state = GameState(self.game_num_players)

        self.state = IN_PROGRESS

        for player in self.players.values():
            print(f"Player {player.name} has number {player.player_number}")
            if player.connected and not player.is_cpu:
                safe_send_message(player, GameStartedMessage.for_player(self, player))

                for msg in self.chat_history:
                    safe_send_message(player, msg)
                for joined_player in self.players.values():
                    safe_send_message(
                        player,
                        PlayerJoinedGameMessage(
                            player_name=joined_player.name,
                            player_number=joined_player.player_number,
                        ),
                    )

        self.broadcast_session_state()

    def handle_message(self, player, msg: ClientMessage):

        if isinstance(msg, ValidatePartialMessage):
            self._handle_validate_partial(player, msg)
        elif isinstance(msg, MoveMessage):
            self._handle_move_message(player, msg)
        elif isinstance(msg, StartGameMessage):
            self._handle_start_game_message(player, msg)
        elif isinstance(msg, ClientChatMessage):
            self._handle_chat(player, msg)
        elif isinstance(msg, UpdateNumPlayersMessage):
            self._handle_update_num_players(player, msg)
        elif isinstance(msg, KickPlayerMessage):
            self._handle_kick_player(player, msg)

    def handle_leave_game(self, player):
        if self.state != IN_PROGRESS:
            return

        player.disconnect()

        self.broadcast_to_game(
            PlayerQuitMessage(
                player_name=player.name,
                player_number=player.player_number,
            )
        )

        self.remove_player(player)

        if player.connection:
            try:
                player.connection.close()
            except:
                pass

    def _handle_chat(self, player, msg: ClientChatMessage):
        message = msg.message.strip()
        if not message:
            return

        chat_msg = ServerChatMessage.from_player(player, message)

        self.chat_history.append(chat_msg)

        # broadcast to everyone (lobby OR game)
        self.broadcast_chat(chat_msg)

    def broadcast_chat(self, message: ServerChatMessage):
        for player in self.players.values():
            if player.connection:
                safe_send_message(player, message)

    def _handle_start_game_message(self, player, msg: StartGameMessage):

        if player.player_id != self.host_player_id:
            return

        if (
            len(self.players) + msg.cpu_count != self.lobby_num_players
            or not self.all_players_connected()
        ):
            return

        self.cpu_count = msg.cpu_count

        self.start_game()

    def _handle_validate_partial(self, player, msg: ValidatePartialMessage):

        path = [tuple(coord) for coord in msg.path]

        response = self.validate_partial_selection(player, path)

        send_message(player.connection, response)

    def _handle_move_message(self, player, msg: MoveMessage):

        path = [tuple(coord) for coord in msg.path]

        result = self.handle_move(player, path)

        if result is not None:
            send_message(player.connection, result)

    def _handle_update_num_players(self, player, msg):

        if player.player_id != self.host_player_id:
            return

        self.lobby_num_players = msg.num_players

        self.broadcast_session_state()

    def handle_leave_lobby(self, player):
        print("session: handle leave lobby")
        if self.state != LOBBY:
            return

        self.remove_player(player)

        player.disconnect()

        if player.connection:
            try:
                player.connection.close()
            except:
                pass

    def _handle_kick_player(self, player, msg):

        if self.state != LOBBY:
            return

        if player.player_id != self.host_player_id:
            return

        target_id = msg.player_id

        if target_id == self.host_player_id:
            return

        target = self.players.get(target_id)

        if not target:
            return

        safe_send_message(target, KickedFromLobbyMessage())

        self.remove_player(target)

        target.disconnect()

        if target.connection:
            try:
                target.connection.close()
            except:
                pass

    def validate_partial_selection(self, player, path):

        assert self.game_state is not None

        with self.lock:
            valid, reason = validate_partial_move(
                self.game_state.board, player.player_number, path
            )

        return PartialValidationMessage(valid=valid, message=reason)

    def handle_move(self, player, path) -> ErrorMessage | None:

        if self.state != IN_PROGRESS:
            return ErrorMessage(message="Game is not active.")

        assert self.game_state is not None

        with self.lock:
            if not self.game_state.is_players_turn(player.player_number):
                return ErrorMessage(message="Not your turn.")

            valid, reason = validate_move(
                self.game_state.board,
                self.game_state.players,
                player.player_number,
                path,
            )

            if not valid:
                return ErrorMessage(message=reason)

            self.game_state.apply_move(path[0], path[-1])

        self.touch()

        self.broadcast_session_state()

        self.process_cpu_turns()

        return None


    def process_cpu_turns(self):

        if self.state != IN_PROGRESS or self.game_state is None:
            return

        while True:
            current_player = self.game_state.current_player_number

            cpu_player = next(
                (
                    p
                    for p in self.players.values()
                    if p.player_number == current_player
                ),
                None,
            )

            if not cpu_player or not cpu_player.is_cpu:
                break

            time.sleep(0.6)

            with self.lock:
                if self.game_state.winner is not None:
                    break

                move = generate_move(
                    self.game_state.board,
                    self.game_state.players,
                    current_player,
                )

                if move is None:
                    print(
                        f"CPU {current_player} has no legal moves — skipping"
                    )
                    self.game_state.next_turn()
                    continue

                self.game_state.apply_move(move[0], move[-1])

            self.touch()

            self.broadcast_session_state()

import time
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


class PlayerConfig(BaseModel):
    player: int
    start: str
    goal: str
    piece: str


class LobbyPlayer(BaseModel):
    player_id: str
    name: str
    player_number: int | None = None
    connected: bool
    is_host: bool


class Identity(BaseModel):
    player_id: str
    name: str
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Server → Client messages
# ---------------------------------------------------------------------------


class WelcomeMessage(BaseModel):
    type: Literal["welcome"] = "welcome"
    player_id: str
    player_number: int | None = None
    players: list[PlayerConfig]
    session_id: str
    chat_history: list["ServerChatMessage"]

    @classmethod
    def for_player(cls, player, session) -> "WelcomeMessage":
        player_configs = session.game_state.players if session.game_state else []
        return cls(
            player_id=player.player_id,
            player_number=player.player_number,
            players=player_configs,
            session_id=session.session_id,
            chat_history=session.chat_history,
        )


class LobbyStateMessage(BaseModel):
    type: Literal["lobby_state"] = "lobby_state"
    players: list[LobbyPlayer]
    session_id: str
    num_players: int
    is_host: bool

    @classmethod
    def for_player(cls, session, player) -> "LobbyStateMessage":
        return cls(
            players=session.serialize_players(),
            session_id=session.session_id,
            num_players=session.lobby_num_players,
            is_host=session.host_player_id == player.player_id,
        )


class GameStateMessage(BaseModel):
    type: Literal["game_state"] = "game_state"
    board: dict[str, int | None]
    current_player: int
    winner: int | None = None

    @classmethod
    def from_game_state(cls, game_state) -> "GameStateMessage":
        return cls(
            board=game_state.serialize_board(),
            current_player=game_state.current_player_number,
            winner=game_state.winner,
        )


class GameStartedMessage(BaseModel):
    type: Literal["game_started"] = "game_started"
    player_number: int
    player_configs: list[PlayerConfig]

    @classmethod
    def for_player(cls, session, player) -> "GameStartedMessage":
        return cls(
            player_number=player.player_number,
            player_configs=session.game_state.players,
        )


class PartialValidationMessage(BaseModel):
    type: Literal["partial_validation"] = "partial_validation"
    valid: bool
    message: str


class PlayerJoinedGameMessage(BaseModel):
    type: Literal["player_joined_game"] = "player_joined_game"
    player_name: str
    player_number: int


class PlayerReconnectedMessage(BaseModel):
    type: Literal["player_reconnected"] = "player_reconnected"
    player_name: str
    player_number: int


class PlayerDisconnectedMessage(BaseModel):
    type: Literal["player_disconnected"] = "player_disconnected"
    player_name: str
    player_number: int


class PlayerQuitMessage(BaseModel):
    type: Literal["player_quit"] = "player_quit"
    player_name: str
    player_number: int


class SessionValidatedMessage(BaseModel):
    type: Literal["session_validated"] = "session_validated"
    session_state: str
    num_players: int
    player_num: int | None = None
    player_configs: list[PlayerConfig] = Field(default_factory=list)

    @classmethod
    def for_session(cls, session, player_num: int | None) -> "SessionValidatedMessage":
        player_configs = session.game_state.players if session.game_state else []
        return cls(
            session_state=session.state,
            num_players=session.lobby_num_players,
            player_num=player_num,
            player_configs=player_configs,
        )


class InvalidSessionMessage(BaseModel):
    type: Literal["invalid_session"] = "invalid_session"


class DuplicatePlayerMessage(BaseModel):
    type: Literal["duplicate_player"] = "duplicate_player"


class KickedFromLobbyMessage(BaseModel):
    type: Literal["kicked_from_lobby"] = "kicked_from_lobby"


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str


class ServerHeartbeatMessage(BaseModel):
    type: Literal["server_heartbeat"] = "server_heartbeat"


class ServerChatMessage(BaseModel):
    type: Literal["chat"] = "chat"
    player_name: str
    player_number: int | None = None
    message: str
    timestamp: float

    @classmethod
    def from_player(cls, player, message: str) -> "ServerChatMessage":
        return cls(
            player_name=player.name,
            player_number=player.player_number,
            message=message,
            timestamp=time.time(),
        )


ServerMessage = Annotated[
    WelcomeMessage
    | LobbyStateMessage
    | GameStateMessage
    | GameStartedMessage
    | PartialValidationMessage
    | PlayerJoinedGameMessage
    | PlayerReconnectedMessage
    | PlayerDisconnectedMessage
    | PlayerQuitMessage
    | SessionValidatedMessage
    | InvalidSessionMessage
    | DuplicatePlayerMessage
    | KickedFromLobbyMessage
    | ErrorMessage
    | ServerHeartbeatMessage
    | ServerChatMessage,
    Field(discriminator="type"),
]

server_adapter = TypeAdapter(ServerMessage)


# ---------------------------------------------------------------------------
# Client → Server messages
# ---------------------------------------------------------------------------


class ConnectMessage(BaseModel):
    type: Literal["connect"] = "connect"
    protocol_version: int
    player_id: str
    name: str
    session_id: str | None = None
    num_players: int | None = None


class MoveMessage(BaseModel):
    type: Literal["move"] = "move"
    path: list[list[int]]


class ValidatePartialMessage(BaseModel):
    type: Literal["validate_partial"] = "validate_partial"
    path: list[list[int]]


class StartGameMessage(BaseModel):
    type: Literal["start_game"] = "start_game"


class UpdateNumPlayersMessage(BaseModel):
    type: Literal["update_num_players"] = "update_num_players"
    num_players: int


class KickPlayerMessage(BaseModel):
    type: Literal["kick_player"] = "kick_player"
    player_id: str


class LeaveLobbyMessage(BaseModel):
    type: Literal["leave_lobby"] = "leave_lobby"


class LeaveGameMessage(BaseModel):
    type: Literal["leave_game"] = "leave_game"


class ClientChatMessage(BaseModel):
    type: Literal["chat"] = "chat"
    message: str


class DebugMessage(BaseModel):
    type: Literal["debug"] = "debug"
    message: str


ClientMessage = Annotated[
    ConnectMessage
    | MoveMessage
    | ValidatePartialMessage
    | StartGameMessage
    | UpdateNumPlayersMessage
    | KickPlayerMessage
    | LeaveLobbyMessage
    | LeaveGameMessage
    | ClientChatMessage
    | DebugMessage,
    Field(discriminator="type"),
]

client_adapter = TypeAdapter(ClientMessage)

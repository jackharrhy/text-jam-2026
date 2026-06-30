# Text-based networked Chinese Checkers
A multiplayer Chinese Checkers game built in Python for [textjam spring2026] (https://textjam.github.io/spring2026/)

## Install
(recommended):
pipx install chinese-checkers-game

or:
pip install chinese-checkers-game

## Play the game
chinese-checkers

## Run a server
chinese-checkers-server

The server listens for TCP clients on `SERVER_PORT` and, by default, WebSocket
clients on `WEBSOCKET_PORT` (`SERVER_PORT + 1`). Set `ENABLE_WEBSOCKET_SERVER=0`
to disable the WebSocket listener.

## License
MIT License

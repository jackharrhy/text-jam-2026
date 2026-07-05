# Text-based networked Chinese Checkers
A multiplayer Chinese Checkers game built in Python for [textjam spring2026](https://textjam.github.io/spring2026/).

## Run locally
Use `uv` from the repository root:

```sh
uv run chinese-checkers
```

## Run a server
```sh
uv run chinese-checkers-server
```

The server listens for TCP clients on `SERVER_PORT` and, by default, serves the
browser client and FastAPI WebSocket endpoint on `WEBSOCKET_PORT`
(`SERVER_PORT + 1`). Open `http://127.0.0.1:5556` locally. Set
`ENABLE_WEBSOCKET_SERVER=0` to disable the browser listener.

## Install from PyPI
If you are not working from a checkout:

```sh
pipx install chinese-checkers-game
```

## License
MIT License

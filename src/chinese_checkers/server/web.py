import asyncio
import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from chinese_checkers.server.protocol import handle_connection
from chinese_checkers.ui.board_layout import HOME_ZONES, ROWS
from chinese_checkers.ui.theme import COLORS

WEB_ROOT = Path(__file__).parents[1] / "web"


class BrowserConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.loop = asyncio.get_running_loop()
        self.closed = False
        self.incoming = queue.Queue()

    def send(self, data: bytes):
        if self.closed:
            return

        message = data.decode("utf-8").rstrip("\n")
        self.loop.call_soon_threadsafe(
            lambda: self.loop.create_task(self.websocket.send_text(message))
        )

    def recv(self, _size: int) -> bytes:
        message = self.incoming.get()

        if message is None:
            return b""

        return f"{message}\n".encode()

    def receive_text(self, message: str):
        if not self.closed:
            self.incoming.put(message)

    def disconnect(self):
        self.closed = True
        self.incoming.put(None)

    def close(self):
        if self.closed:
            return

        self.closed = True
        self.incoming.put(None)
        self.loop.call_soon_threadsafe(
            lambda: self.loop.create_task(self.websocket.close())
        )


def create_app(manager) -> FastAPI:
    app = FastAPI(title="Chinese Checkers Web")
    templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))

    app.mount(
        "/static",
        StaticFiles(directory=str(WEB_ROOT / "static")),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(request, "index.html", {})

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/game", response_class=HTMLResponse)
    async def game(
        request: Request,
        name: str,
        session_id: str | None = None,
        spectator: bool = False,
    ):
        return templates.TemplateResponse(
            request,
            "game.html",
            {
                "name": name,
                "session_id": session_id or "",
                "spectator": spectator,
                "rows_json": json.dumps(ROWS),
                "home_zones_json": json.dumps(
                    {
                        zone: [list(coord) for coord in coords]
                        for zone, coords in HOME_ZONES.items()
                    }
                ),
                "colors_json": json.dumps(COLORS),
            },
        )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        conn = BrowserConnection(websocket)
        thread = threading.Thread(
            target=handle_connection,
            args=(manager, conn),
            daemon=True,
        )
        thread.start()

        try:
            while not conn.closed:
                conn.receive_text(await websocket.receive_text())
        except WebSocketDisconnect:
            pass
        finally:
            conn.disconnect()
            await asyncio.to_thread(thread.join, 1)

    return app

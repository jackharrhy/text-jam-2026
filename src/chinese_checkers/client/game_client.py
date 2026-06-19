import socket
import threading
import time
from chinese_checkers.shared.network import send_json, receive_json
from chinese_checkers.shared.message_types import CONNECT, DEBUG, SERVER_HEARTBEAT
from chinese_checkers.shared.settings import PROTOCOL_VERSION, SERVER_TIMEOUT


class GameClient:
    def __init__(self):
        self.socket = None
        self.receive_thread = None
        self.watchdog_thread = None

        self.running = False
        self.last_server_heartbeat = None

        self.buffer = ""

        self.on_message = None
        self.on_disconnect = None
        self.log_message = None

        self.identity = None

    def connect(self, host, port):

        if self.socket:
            self.close()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

        self.buffer = ""

        self.running = True
        self.last_server_heartbeat = time.time()

        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()

        self.watchdog_thread = threading.Thread(
            target=self.connection_watchdog, daemon=True
        )
        self.watchdog_thread.start()

    def connect_to_session(
        self, host, port, identity, session_id=None, num_players=None
    ):

        self.connect(host, port)

        self.send(
            {
                "type": CONNECT,
                "protocol_version": PROTOCOL_VERSION,
                "player_id": identity["player_id"],
                "session_id": session_id,
                "name": identity["name"],
                "num_players": num_players,
            }
        )

    def send(self, data):

        if not self.socket:
            return False

        try:
            send_json(self.socket, data)

            return True

        except (BrokenPipeError, ConnectionResetError, OSError):
            self._handle_disconnect()

            return False

    def close(self):
        self.running = False
        if self.socket:
            self.socket.close()

    def _receive_loop(self):
        while self.running:
            try:
                data, self.buffer = receive_json(self.socket, self.buffer)

                if data is None:
                    self._handle_disconnect()
                    return

                if data["type"] == SERVER_HEARTBEAT:
                    self.last_server_heartbeat = time.time()
                    continue

                if self.on_message:
                    self.on_message(data)

            except Exception as e:
                self.send({"type": DEBUG, "message": f"EXCEPTION: GAME_CLIENT.PY: {e}"})

                self._handle_disconnect()
                return

        self.running = False

    def connection_watchdog(self):

        while self.running:
            time.sleep(5)

            if time.time() - self.last_server_heartbeat > SERVER_TIMEOUT:
                if self.log_message:
                    self.log_message(
                        "GAME_CLIENT.PY: HAVEN'T HEARD FROM SERVER IN 30 SECONDS"
                    )

                self._handle_disconnect()

                break

    def _handle_disconnect(self):

        if not self.running:
            return

        self.running = False

        try:
            self.socket.close()
        except:
            pass

        self.socket = None

        if self.on_disconnect:
            self.on_disconnect()

    def dispatch_to_ui(self, app, callback, *args):

        app.call_from_thread(callback, *args)

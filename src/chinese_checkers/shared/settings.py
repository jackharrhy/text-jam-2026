import os

from dotenv import load_dotenv

load_dotenv()

PUBLIC_SERVER_HOST = os.environ.get("PUBLIC_SERVER_HOST", "chinesecheckers.webhop.me")
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "5555"))
WEBSOCKET_LISTEN_HOST = os.environ.get("WEBSOCKET_LISTEN_HOST", LISTEN_HOST)
WEBSOCKET_PORT = int(os.environ.get("WEBSOCKET_PORT", str(SERVER_PORT + 1)))
ENABLE_WEBSOCKET_SERVER = os.environ.get("ENABLE_WEBSOCKET_SERVER", "1") == "1"
PROTOCOL_VERSION = 2
HEARTBEAT_INTERVAL = 10
SERVER_TIMEOUT = 30

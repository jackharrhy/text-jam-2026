import time


class Player:
    def __init__(self, player_id, name, session_id, player_number=None):

        self.player_id = player_id
        self.name = name
        self.session_id = session_id
        self.player_number = player_number

        self.connection = None

        self.connected = False

        self.last_seen = time.time()

    def attach_connection(self, conn):

        self.connection = conn
        self.connected = True

        self.last_seen = time.time()

    def disconnect(self):

        self.connection = None
        self.connected = False

        self.last_seen = time.time()

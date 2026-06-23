import random
import string
import threading

from chinese_checkers.server.session import Session


class SessionManager:
    def __init__(self):

        self.sessions = {}
        self.lock = threading.Lock()

    def generate_session_id(self):

        letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"

        while True:
            session_id = "".join(random.choice(letters) for _ in range(4))

            if session_id not in self.sessions:
                return session_id

    def create_session(self, num_players):

        with self.lock:
            session_id = self.generate_session_id()

            session = Session(session_id=session_id, num_players=num_players)

            self.sessions[session_id] = session

        return session

    def get_session(self, session_id):

        with self.lock:
            return self.sessions.get(session_id)

    def cleanup_sessions(self):

        abandoned = []

        with self.lock:
            sessions_copy = list(self.sessions.items())

            for session_id, session in sessions_copy:
                if session.is_abandoned():
                    abandoned.append(session_id)

        for session_id in abandoned:
            print(f"Cleaning up session {session_id}")

            with self.lock:
                self.sessions.pop(session_id, None)

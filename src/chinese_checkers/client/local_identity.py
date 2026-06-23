import json
from pathlib import Path

IDENTIFY_FILE = Path.home() / ".chinese_checkers_identity.json"


def load_identity():

    if not IDENTIFY_FILE.exists():
        return None

    with open(IDENTIFY_FILE, "r") as f:
        return json.load(f)


def save_identity(identity):

    with open(IDENTIFY_FILE, "w") as f:
        json.dump(identity, f)


def clear_identity():

    if IDENTIFY_FILE.exists():
        IDENTIFY_FILE.unlink()

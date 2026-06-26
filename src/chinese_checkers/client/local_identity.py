from pathlib import Path

from chinese_checkers.shared.models import Identity

IDENTIFY_FILE = Path.home() / ".chinese_checkers_identity.json"


def load_identity():

    if not IDENTIFY_FILE.exists():
        return None

    return Identity.model_validate_json(IDENTIFY_FILE.read_text())


def save_identity(identity: Identity):

    IDENTIFY_FILE.write_text(identity.model_dump_json())


def clear_identity():

    if IDENTIFY_FILE.exists():
        IDENTIFY_FILE.unlink()

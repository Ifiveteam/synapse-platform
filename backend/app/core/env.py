"""Load backend/.env regardless of shell working directory."""

from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


def load_backend_env() -> None:
    load_dotenv(_ENV_FILE)

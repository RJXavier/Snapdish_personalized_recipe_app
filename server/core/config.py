"""Central configuration, read from environment variables (or server/.env)."""
import os
import secrets
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None

SERVER_DIR = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    load_dotenv(SERVER_DIR / ".env")

# Database. MySQL is the reference database; when DATABASE_URL is not set the
# server falls back to a local SQLite file so the project runs with zero setup.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(SERVER_DIR / 'rec_app.db').as_posix()}"
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"

# Uploaded fridge photos
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR") or SERVER_DIR / "uploads")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024

# YOLO weights
MODEL_PATH = Path(os.getenv("MODEL_PATH") or SERVER_DIR / "best.pt")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(24 * 60)))


def _load_jwt_secret() -> str:
    """Use JWT_SECRET_KEY when provided, otherwise create a random secret once
    and keep it in a git-ignored file so tokens survive server restarts."""
    secret = os.getenv("JWT_SECRET_KEY")
    if secret:
        return secret
    secret_file = SERVER_DIR / ".jwt_secret"
    if secret_file.exists():
        stored = secret_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    secret = secrets.token_urlsafe(48)
    secret_file.write_text(secret, encoding="utf-8")
    return secret


JWT_SECRET_KEY = _load_jwt_secret()

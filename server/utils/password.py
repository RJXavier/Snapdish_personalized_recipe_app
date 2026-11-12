import hashlib
import re

import bcrypt

_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_legacy_hash(stored_hash: str) -> bool:
    """Earlier versions of this project stored unsalted MD5 hashes."""
    return bool(_MD5_RE.match(stored_hash or ""))


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if is_legacy_hash(stored_hash):
        legacy = hashlib.md5(password.encode("utf-8")).hexdigest()
        return legacy.lower() == stored_hash.lower()
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False

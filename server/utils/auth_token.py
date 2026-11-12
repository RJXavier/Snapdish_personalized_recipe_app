from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY

ALGORITHM = "HS256"


class TokenUtils:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return None

    @staticmethod
    def create_user_token(user_id: int, username: str) -> str:
        return TokenUtils.create_access_token({"user_id": user_id, "username": username})

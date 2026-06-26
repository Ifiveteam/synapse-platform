from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "synapse-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def create_access_token(user_id: uuid.UUID | str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return uuid.UUID(sub) if sub else None
    except (JWTError, ValueError, TypeError):
        return None

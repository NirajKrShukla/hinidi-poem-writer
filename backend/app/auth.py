from datetime import datetime, timedelta
import jwt
from .config import settings


def create_jwt(user_info: dict | None = None, user_id: int | None = None, expires_days: int = 7) -> str:
    sub = None
    name = None
    if user_info:
        sub = user_info.get("email") or user_info.get("sub")
        name = user_info.get("name")
    if user_id:
        sub = f"user:{user_id}" if not sub else sub
    payload = {
        "sub": sub,
        "name": name,
        "iat": datetime.utcnow().timestamp(),
        "exp": (datetime.utcnow() + timedelta(days=expires_days)).timestamp(),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_jwt(token: str) -> dict:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return data
    except Exception:
        raise

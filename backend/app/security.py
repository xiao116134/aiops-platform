from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt

from .config import settings

ALGORITHM = 'HS256'


def _create_token(payload: dict, expire_minutes: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    token_payload = {
        **payload,
        'exp': expire,
    }
    return jwt.encode(token_payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_access_token(username: str, role: str) -> str:
    return _create_token(
        {
            'sub': username,
            'role': role,
            'type': 'access',
        },
        settings.jwt_expire_minutes,
    )


def create_refresh_token(username: str, role: str) -> str:
    return _create_token(
        {
            'sub': username,
            'role': role,
            'type': 'refresh',
        },
        settings.jwt_expire_minutes * 24,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except JWTError as error:
        raise HTTPException(status_code=401, detail='Token 无效或已过期') from error

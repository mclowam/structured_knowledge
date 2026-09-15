import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.core.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    username: str
    is_staff: bool


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "access":
            raise ValueError("token is not an access token")
        user_id = uuid.UUID(str(payload["user_id"]))
        username = payload["username"]
        if not isinstance(username, str) or not username:
            raise ValueError("token has no username")
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise credentials_exception from exc

    return CurrentUser(
        user_id=user_id,
        username=username,
        is_staff=bool(payload.get("is_staff", False)),
    )

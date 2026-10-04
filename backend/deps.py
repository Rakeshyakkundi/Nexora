"""Shared FastAPI dependencies."""

from fastapi import Header, HTTPException

from backend.store import get_session_user


async def get_current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ")
    username = get_session_user(token)
    if not username:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return username

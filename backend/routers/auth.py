from fastapi import APIRouter, Depends, Header, HTTPException

from backend.auth import hash_password, new_token, verify_password
from backend.deps import get_current_user
from backend.models import AuthResponse, LoginRequest, MeResponse, ResetPasswordRequest, SignupRequest
from backend.store import (
    create_session,
    create_user,
    delete_session,
    get_user_by_email,
    get_user_by_username,
    update_user_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(body: SignupRequest):
    if get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="That username is already taken.")
    if get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="That email is already registered.")
    if not body.username.strip() or not body.email.strip() or not body.password:
        raise HTTPException(status_code=400, detail="Username, email, and password are all required.")

    create_user(body.username, body.email, hash_password(body.password))

    token = new_token()
    create_session(token, body.username)
    return AuthResponse(token=token, username=body.username, email=body.email)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    user = get_user_by_username(body.username)
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that username.")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    token = new_token()
    create_session(token, user["username"])
    return AuthResponse(token=token, username=user["username"], email=user["email"])


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(body: ResetPasswordRequest):
    """Basic reset: matches by email and sets a new password directly, no
    verification email/link - by design, per this prototype's scope.
    """
    user = get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email.")
    if not body.new_password:
        raise HTTPException(status_code=400, detail="A new password is required.")

    update_user_password(user["username"], hash_password(body.new_password))

    token = new_token()
    create_session(token, user["username"])
    return AuthResponse(token=token, username=user["username"], email=user["email"])


@router.get("/me", response_model=MeResponse)
async def me(current_user: str = Depends(get_current_user)):
    user = get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return MeResponse(username=user["username"], email=user["email"])


@router.post("/logout", status_code=204)
async def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        delete_session(authorization.removeprefix("Bearer "))

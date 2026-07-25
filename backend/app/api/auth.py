"""Auth API — register, login, current user."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.auth_service import UserOut, auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """Register a new user and return a JWT token."""
    try:
        user = await auth_service.register(req.username, req.password, req.display_name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    token = auth_service.create_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate and return a JWT token."""
    user = await auth_service.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = auth_service.create_token(user.id)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
async def me(user: UserOut = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user

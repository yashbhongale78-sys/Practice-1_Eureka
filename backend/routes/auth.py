"""
routes/auth.py — Registration and login endpoints.
"""

from fastapi import APIRouter
from backend.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from backend.services.auth_service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(data: RegisterRequest):
    """Register a new citizen account."""
    return await register_user(data)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Authenticate and receive a JWT token."""
    return await login_user(data)

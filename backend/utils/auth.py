"""
utils/auth.py — JWT token verification and FastAPI dependency injection.
Supabase issues JWTs signed with the project's JWT secret.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from backend.config import get_settings
from backend.database.client import get_supabase

bearer_scheme = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    Decode and validate a Supabase-issued JWT.
    Returns the decoded payload (includes user id as 'sub').
    """
    settings = get_settings()
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False}  # Supabase tokens have dynamic audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


def get_current_user(payload: dict = Depends(verify_token)) -> dict:
    """Extract user info from JWT payload."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user id"
        )
    return {
        "user_id": user_id,
        "email": payload.get("email", ""),
        "role": payload.get("user_metadata", {}).get("role", "citizen")
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that enforces admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

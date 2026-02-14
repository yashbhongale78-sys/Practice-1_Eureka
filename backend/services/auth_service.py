"""
services/auth_service.py — User registration and login using Supabase Auth.
Returns JWT tokens issued by Supabase.
"""

from fastapi import HTTPException, status
from backend.database.client import get_supabase_anon
from backend.schemas.auth import RegisterRequest, LoginRequest, AuthResponse


async def register_user(data: RegisterRequest) -> AuthResponse:
    """
    Create a new user in Supabase Auth and set their role metadata.
    Default role is 'citizen'; promote to 'admin' manually in Supabase dashboard.
    """
    sb = get_supabase_anon()

    try:
        result = sb.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "full_name": data.full_name,
                    "role": "citizen"  # Default role
                }
            }
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

    if not result.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Email may already be in use."
        )

    # Insert into our users table (mirror of auth.users)
    sb_admin = get_supabase_anon()
    try:
        sb_admin.table("users").insert({
            "id": result.user.id,
            "email": data.email,
            "role": "citizen"
        }).execute()
    except Exception:
        pass  # Non-fatal if users table already has triggers

    token = result.session.access_token if result.session else ""
    return AuthResponse(
        access_token=token,
        user_id=result.user.id,
        email=result.user.email,
        role="citizen"
    )


async def login_user(data: LoginRequest) -> AuthResponse:
    """Authenticate user with email/password and return JWT."""
    sb = get_supabase_anon()

    try:
        result = sb.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not result.user or not result.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed"
        )

    role = result.user.user_metadata.get("role", "citizen")
    return AuthResponse(
        access_token=result.session.access_token,
        user_id=result.user.id,
        email=result.user.email,
        role=role
    )

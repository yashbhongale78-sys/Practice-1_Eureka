"""
config.py — Central configuration using environment variables.
All secrets and settings come from a .env file or system environment.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Gemini AI
    gemini_api_key: str

    # JWT (Supabase generates JWTs, we use its secret to verify)
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # App
    app_env: str = "development"
    app_name: str = "CivicIQ"
    cors_origins: str = "*"

    # Rate limiting (in-memory: max complaints per user per hour)
    rate_limit_complaints: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — reads .env once at startup."""
    return Settings()

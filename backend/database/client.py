"""
database/client.py — Supabase client singleton.
Uses the service role key for admin operations (server-side only).
"""

from supabase import create_client, Client
from backend.config import get_settings

_supabase_client: Client | None = None


def get_supabase() -> Client:
    """Return a shared Supabase client (service role — server use only)."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key  # Service key bypasses RLS
        )
    return _supabase_client


def get_supabase_anon() -> Client:
    """Return a Supabase client using the anon key (public, respects RLS)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)

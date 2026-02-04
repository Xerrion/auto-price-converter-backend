"""Database client initialization."""

from app.core.config import get_settings
from supabase import Client, create_client


def get_supabase_client() -> Client:
    """Get Supabase client."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

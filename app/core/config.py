"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # External APIs
    fixer_api_key: str | None = None

    # Security
    sync_api_key: str | None = None

    # Sync settings
    sync_interval_hours: int = 24
    symbols_cache_hours: int = 4320  # 180 days

    # Providers
    provider_priority: str = "fixer,frankfurter"

    # CORS
    allow_origins: str = "*"

    # Logging
    log_level: str = "INFO"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cache_ttl_seconds(self) -> int:
        """Calculate cache TTL based on sync interval."""
        return self.sync_interval_hours * 60 * 60

    @property
    def symbols_cache_ttl_seconds(self) -> int:
        """Calculate symbols cache TTL."""
        return self.symbols_cache_hours * 60 * 60

    @property
    def origins_list(self) -> list[str]:
        """Parse ALLOW_ORIGINS into a list."""
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]

    @property
    def provider_priority_list(self) -> list[str]:
        """Parse PROVIDER_PRIORITY into a list."""
        return [p.strip() for p in self.provider_priority.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

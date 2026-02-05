"""Tests for application configuration."""

from app.core.config import Settings


class TestSettings:
    """Tests for Settings class."""

    def test_cache_ttl_computed_from_hours(self) -> None:
        """cache_ttl_seconds is computed from sync_interval_hours."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_interval_hours=24,
        )

        assert settings.cache_ttl_seconds == 24 * 60 * 60  # 86400

    def test_cache_ttl_different_hours(self) -> None:
        """cache_ttl_seconds changes with different hours."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_interval_hours=12,
        )

        assert settings.cache_ttl_seconds == 12 * 60 * 60  # 43200

    def test_origins_list_parsing_single(self) -> None:
        """Single origin is parsed correctly."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            allow_origins="https://example.com",
        )

        assert settings.origins_list == ["https://example.com"]

    def test_origins_list_parsing_multiple(self) -> None:
        """Multiple origins are parsed correctly."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            allow_origins="https://example.com,https://api.example.com",
        )

        assert settings.origins_list == ["https://example.com", "https://api.example.com"]

    def test_origins_list_strips_whitespace(self) -> None:
        """Whitespace is stripped from origins."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            allow_origins="  https://example.com  ,  https://api.example.com  ",
        )

        assert settings.origins_list == ["https://example.com", "https://api.example.com"]

    def test_origins_list_filters_empty(self) -> None:
        """Empty strings are filtered out."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            allow_origins="https://example.com,,https://api.example.com",
        )

        assert settings.origins_list == ["https://example.com", "https://api.example.com"]

    def test_provider_priority_parsing(self) -> None:
        """Provider priority is parsed correctly."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            provider_priority="fixer,frankfurter",
        )

        assert settings.provider_priority_list == ["fixer", "frankfurter"]

    def test_provider_priority_strips_whitespace(self) -> None:
        """Whitespace is stripped from providers."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            provider_priority="  fixer  ,  frankfurter  ",
        )

        assert settings.provider_priority_list == ["fixer", "frankfurter"]

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
        )

        assert settings.sync_interval_hours == 24
        assert settings.provider_priority == "fixer,frankfurter"
        assert settings.allow_origins == "*"
        assert settings.log_level == "INFO"
        assert settings.environment == "development"

    def test_optional_api_keys(self) -> None:
        """Optional API keys default to None."""
        # Disable env file loading to test true defaults
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            _env_file=None,
        )

        assert settings.fixer_api_key is None
        assert settings.sync_api_key is None

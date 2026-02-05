"""Tests for security dependencies."""

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.dependencies import verify_api_key


class TestVerifyApiKey:
    """Tests for verify_api_key function."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_key(self) -> None:
        """Returns the API key when it matches."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_api_key="secret-key",
        )

        result = await verify_api_key("secret-key", settings)

        assert result == "secret-key"

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self) -> None:
        """Raises 401 HTTPException when key doesn't match."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_api_key="secret-key",
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key("wrong-key", settings)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_no_key_provided_raises_401(self) -> None:
        """Raises 401 HTTPException when no key is provided but one is required."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_api_key="secret-key",
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(None, settings)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_key_configured_returns_provided_key(self) -> None:
        """Returns provided key when no sync_api_key is configured."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_api_key=None,  # No API key required
        )

        result = await verify_api_key("any-key", settings)

        assert result == "any-key"

    @pytest.mark.asyncio
    async def test_no_key_configured_no_key_provided_returns_none(self) -> None:
        """Returns None when no key is configured and none is provided."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_service_role_key="test-key",
            sync_api_key=None,  # No API key required
        )

        result = await verify_api_key(None, settings)

        assert result is None

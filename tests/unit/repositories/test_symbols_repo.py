"""Tests for SymbolsRepository."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.repositories.symbols import SymbolsRepository


class TestSymbolsRepositoryInit:
    """Tests for SymbolsRepository initialization."""

    def test_init_sets_attributes(self) -> None:
        """Constructor sets supabase client and cache_ttl_seconds."""
        mock_supabase = MagicMock()
        cache_ttl = 86400

        repo = SymbolsRepository(mock_supabase, cache_ttl)

        assert repo.supabase is mock_supabase
        assert repo.cache_ttl_seconds == cache_ttl


class TestStoreSymbols:
    """Tests for store_symbols method."""

    def test_store_symbols_success(self) -> None:
        """Successfully stores symbols."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "test-symbols-id"}]
        )

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.store_symbols("fixer", {"USD": "US Dollar", "EUR": "Euro"})

        assert result == "test-symbols-id"
        mock_supabase.table.assert_called_with("symbols_runs")

    def test_store_symbols_db_failure(self) -> None:
        """Raises RuntimeError when database insert fails."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )

        repo = SymbolsRepository(mock_supabase, 86400)

        with pytest.raises(RuntimeError, match="Failed to insert symbols run"):
            repo.store_symbols("fixer", {"USD": "US Dollar"})


class TestGetLatest:
    """Tests for get_latest method."""

    def test_get_latest_success(self) -> None:
        """Returns formatted symbols data."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "fetched_at": "2024-02-04T12:00:00+00:00",
                    "symbols": {"USD": "US Dollar", "EUR": "Euro"},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.get_latest("fixer")

        assert result is not None
        assert result["provider"] == "fixer"
        assert result["symbols"]["USD"] == "US Dollar"

    def test_get_latest_not_found(self) -> None:
        """Returns None when no data found."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(data=[])
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.get_latest("nonexistent")

        assert result is None

    def test_get_latest_empty_symbols(self) -> None:
        """Handles None/empty symbols gracefully."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "fetched_at": "2024-02-04T12:00:00+00:00",
                    "symbols": None,
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.get_latest("fixer")

        assert result is not None
        assert result["symbols"] == {}


class TestIsFresh:
    """Tests for is_fresh method."""

    def test_is_fresh_returns_true(self) -> None:
        """Returns True when data is within TTL."""
        mock_supabase = MagicMock()
        fresh_time = datetime.now(tz=UTC).isoformat()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "fetched_at": fresh_time,
                    "symbols": {"USD": "US Dollar"},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)  # 24 hours
        result = repo.is_fresh("fixer")

        assert result is True

    def test_is_fresh_returns_false_stale(self) -> None:
        """Returns False when data is older than TTL."""
        mock_supabase = MagicMock()
        stale_time = (datetime.now(tz=UTC) - timedelta(hours=25)).isoformat()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "fetched_at": stale_time,
                    "symbols": {"USD": "US Dollar"},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)  # 24 hours
        result = repo.is_fresh("fixer")

        assert result is False

    def test_is_fresh_no_data(self) -> None:
        """Returns False when no cached data exists."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(data=[])
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.is_fresh("fixer")

        assert result is False

    def test_is_fresh_invalid_timestamp(self) -> None:
        """Returns False when timestamp is invalid."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "fetched_at": "invalid-timestamp",
                    "symbols": {"USD": "US Dollar"},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.is_fresh("fixer")

        assert result is False

    def test_is_fresh_naive_datetime(self) -> None:
        """Handles naive datetime (no timezone) correctly."""
        mock_supabase = MagicMock()
        # Naive datetime without timezone
        naive_time = datetime.now().isoformat()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "fetched_at": naive_time,
                    "symbols": {"USD": "US Dollar"},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = SymbolsRepository(mock_supabase, 86400)
        result = repo.is_fresh("fixer")

        # Should handle naive datetime and return True (since it's recent)
        assert result is True

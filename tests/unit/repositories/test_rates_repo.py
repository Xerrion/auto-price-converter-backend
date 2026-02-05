"""Tests for RatesRepository."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.repositories.rates import RatesRepository


class TestRatesRepositoryInit:
    """Tests for RatesRepository initialization."""

    def test_init_sets_attributes(self) -> None:
        """Constructor sets supabase client and cache_ttl_seconds."""
        mock_supabase = MagicMock()
        cache_ttl = 86400

        repo = RatesRepository(mock_supabase, cache_ttl)

        assert repo.supabase is mock_supabase
        assert repo.cache_ttl_seconds == cache_ttl


class TestStoreRun:
    """Tests for store_run method."""

    def test_store_run_success(self) -> None:
        """Successfully stores rates run and entries."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "test-run-id"}]
        )

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.store_run("fixer", "EUR", "2024-02-04", {"USD": 1.08, "GBP": 0.85})

        assert result == "test-run-id"
        # Verify rates_runs table was called
        mock_supabase.table.assert_any_call("rates_runs")
        # Verify rates_entries table was called
        mock_supabase.table.assert_any_call("rates_entries")

    def test_store_run_empty_rates(self) -> None:
        """Stores run with no rate entries."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "test-run-id"}]
        )

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.store_run("fixer", "EUR", "2024-02-04", {})

        assert result == "test-run-id"
        # rates_entries should not be called for empty rates
        calls = [call[0][0] for call in mock_supabase.table.call_args_list]
        assert calls.count("rates_entries") == 0

    def test_store_run_db_failure(self) -> None:
        """Raises RuntimeError when database insert fails."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )

        repo = RatesRepository(mock_supabase, 86400)

        with pytest.raises(RuntimeError, match="Failed to insert rates run"):
            repo.store_run("fixer", "EUR", "2024-02-04", {"USD": 1.08})


class TestGetLatestRun:
    """Tests for get_latest_run method."""

    def test_get_latest_run_success(self) -> None:
        """Returns formatted run data."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "combined",
                    "base": "EUR",
                    "date": "2024-02-04",
                    "fetched_at": "2024-02-04T12:00:00+00:00",
                    "rates": {"USD": 1.08, "GBP": 0.85},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.get_latest_run("combined")

        assert result is not None
        assert result["provider"] == "combined"
        assert result["base"] == "EUR"
        assert result["date"] == "2024-02-04"
        assert result["rates"]["USD"] == 1.08

    def test_get_latest_run_not_found(self) -> None:
        """Returns None when no data found."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(data=[])
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.get_latest_run("nonexistent")

        assert result is None

    def test_get_latest_run_empty_rates(self) -> None:
        """Handles None/empty rates gracefully."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "combined",
                    "base": "EUR",
                    "date": "2024-02-04",
                    "fetched_at": "2024-02-04T12:00:00+00:00",
                    "rates": None,
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.get_latest_run("combined")

        assert result is not None
        assert result["rates"] == {}


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
                    "base": "EUR",
                    "date": "2024-02-04",
                    "fetched_at": fresh_time,
                    "rates": {"USD": 1.08},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)  # 24 hours
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
                    "base": "EUR",
                    "date": "2024-02-04",
                    "fetched_at": stale_time,
                    "rates": {"USD": 1.08},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)  # 24 hours
        result = repo.is_fresh("fixer")

        assert result is False

    def test_is_fresh_no_data(self) -> None:
        """Returns False when no cached data exists."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(data=[])
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.is_fresh("fixer")

        assert result is False

    def test_is_fresh_invalid_timestamp(self) -> None:
        """Returns False when timestamp is invalid."""
        mock_supabase = MagicMock()
        mock_execute = MagicMock(
            data=[
                {
                    "provider": "fixer",
                    "base": "EUR",
                    "date": "2024-02-04",
                    "fetched_at": "invalid-timestamp",
                    "rates": {"USD": 1.08},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)
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
                    "base": "EUR",
                    "date": "2024-02-04",
                    "fetched_at": naive_time,
                    "rates": {"USD": 1.08},
                }
            ]
        )
        mock_chain = mock_supabase.table.return_value.select.return_value
        mock_chain.eq.return_value.limit.return_value.execute.return_value = mock_execute

        repo = RatesRepository(mock_supabase, 86400)
        result = repo.is_fresh("fixer")

        # Should handle naive datetime and return True (since it's recent)
        assert result is True

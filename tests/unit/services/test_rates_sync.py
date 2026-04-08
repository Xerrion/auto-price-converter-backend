"""Tests for RatesSyncService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.rates_sync import RatesSyncService, _fmt_duration


class TestMergeRates:
    """Tests for merge_rates method."""

    def test_priority_order_first_provider_wins(self) -> None:
        """Higher priority provider wins for same currency."""
        service = RatesSyncService(
            rates_repo=MagicMock(),
            symbols_repo=MagicMock(),
            provider_service=MagicMock(),
            provider_priority=["fixer", "frankfurter"],
        )

        provider_rates = {
            "fixer": {"USD": 1.08, "GBP": 0.85},
            "frankfurter": {"USD": 1.09, "JPY": 161.0},  # Different USD rate
        }

        result = service.merge_rates(provider_rates, ["fixer", "frankfurter"])

        # Fixer's USD rate should win (higher priority)
        assert result["USD"] == 1.08

    def test_combines_unique_currencies(self) -> None:
        """All unique currencies from all providers are included."""
        service = RatesSyncService(
            rates_repo=MagicMock(),
            symbols_repo=MagicMock(),
            provider_service=MagicMock(),
            provider_priority=["fixer", "frankfurter"],
        )

        provider_rates = {
            "fixer": {"USD": 1.08, "GBP": 0.85},
            "frankfurter": {"JPY": 161.0, "CHF": 0.94},
        }

        result = service.merge_rates(provider_rates, ["fixer", "frankfurter"])

        assert "USD" in result
        assert "GBP" in result
        assert "JPY" in result
        assert "CHF" in result

    def test_always_includes_eur(self) -> None:
        """EUR=1.0 is always in the result."""
        service = RatesSyncService(
            rates_repo=MagicMock(),
            symbols_repo=MagicMock(),
            provider_service=MagicMock(),
            provider_priority=["fixer"],
        )

        provider_rates = {"fixer": {"USD": 1.08}}

        result = service.merge_rates(provider_rates, ["fixer"])

        assert result["EUR"] == 1.0

    def test_empty_providers_returns_only_eur(self) -> None:
        """Empty provider dict returns only EUR=1.0."""
        service = RatesSyncService(
            rates_repo=MagicMock(),
            symbols_repo=MagicMock(),
            provider_service=MagicMock(),
            provider_priority=["fixer"],
        )

        result = service.merge_rates({}, ["fixer"])

        assert result == {"EUR": 1.0}

    def test_missing_provider_in_rates_skipped(self) -> None:
        """Providers not in provider_rates are skipped."""
        service = RatesSyncService(
            rates_repo=MagicMock(),
            symbols_repo=MagicMock(),
            provider_service=MagicMock(),
            provider_priority=["fixer", "frankfurter"],
        )

        provider_rates = {"fixer": {"USD": 1.08}}  # No frankfurter

        result = service.merge_rates(provider_rates, ["fixer", "frankfurter"])

        assert result["USD"] == 1.08
        assert result["EUR"] == 1.0


class TestSyncAllRates:
    """Tests for sync_all_rates method."""

    def test_skips_fresh_providers(self) -> None:
        """Skips providers with fresh cache when force=False."""
        fresh_row = {"fetched_at": "2024-02-04T12:00:00+00:00"}
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = fresh_row
        mock_rates_repo.cache_ttl_seconds = 86400

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = fresh_row
        mock_symbols_repo.cache_ttl_seconds = 86400

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods (used by sync_all_rates)
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        # Should skip all providers
        assert result["providers"]["fixer"]["skipped"] == "fresh-cache"
        assert result["providers"]["frankfurter"]["skipped"] == "fresh-cache"

    def test_force_ignores_fresh_cache(self) -> None:
        """Fetches even when fresh if force=True."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None
        mock_symbols_repo.store_symbols.return_value = "test-symbols-id"

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods (used by sync_all_rates)
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        mock_provider_service.fetch_fixer.return_value = {
            "provider": "fixer",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.08},
        }
        mock_provider_service.fetch_frankfurter.return_value = {
            "provider": "frankfurter",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"JPY": 161.0},
        }
        mock_provider_service.fetch_fixer_symbols.return_value = {
            "provider": "fixer",
            "symbols": {"USD": "US Dollar"},
        }

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=True)

        # Should have run_id, not skipped
        assert "run_id" in result["providers"]["fixer"]
        assert "run_id" in result["providers"]["frankfurter"]
        assert "run_id" in result["providers"]["combined"]

    def test_creates_combined_rates(self) -> None:
        """Combined rates are created from provider rates."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None
        mock_symbols_repo.store_symbols.return_value = "test-symbols-id"

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods (used by sync_all_rates)
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        mock_provider_service.fetch_fixer.return_value = {
            "provider": "fixer",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.08},
        }
        mock_provider_service.fetch_frankfurter.return_value = {
            "provider": "frankfurter",
            "base": "EUR",
            "date": "2024-02-05",
            "rates": {"JPY": 161.0},
        }
        mock_provider_service.fetch_fixer_symbols.return_value = {
            "provider": "fixer",
            "symbols": {"USD": "US Dollar"},
        }

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        # Combined should be created
        assert "run_id" in result["providers"]["combined"]

        # Verify store_run was called for combined
        combined_call = [
            call for call in mock_rates_repo.store_run.call_args_list if call[0][0] == "combined"
        ]
        assert len(combined_call) == 1
        # Combined date should be max of provider dates
        assert combined_call[0][0][2] == "2024-02-05"

    def test_handles_provider_error_gracefully(self) -> None:
        """Continues on individual provider failure."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None
        mock_symbols_repo.store_symbols.return_value = "test-symbols-id"

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods (used by sync_all_rates)
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        mock_provider_service.fetch_fixer.side_effect = RuntimeError("Fixer API error")
        mock_provider_service.fetch_frankfurter.return_value = {
            "provider": "frankfurter",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"JPY": 161.0},
        }
        mock_provider_service.fetch_fixer_symbols.return_value = None

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        # Fixer should have error, frankfurter should succeed
        assert "error" in result["providers"]["fetch_fixer"]
        assert "run_id" in result["providers"]["frankfurter"]

    def test_syncs_symbols(self) -> None:
        """Symbols sync is called."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None
        mock_symbols_repo.store_symbols.return_value = "test-symbols-id"

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods (used by sync_all_rates)
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        mock_provider_service.fetch_fixer.return_value = {
            "provider": "fixer",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.08},
        }
        mock_provider_service.fetch_frankfurter.return_value = None
        mock_provider_service.fetch_fixer_symbols.return_value = {
            "provider": "fixer",
            "symbols": {"USD": "US Dollar", "EUR": "Euro"},
        }

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        # Symbols should be synced
        assert "run_id" in result["providers"]["symbols"]
        mock_symbols_repo.store_symbols.assert_called_once()

    def test_symbols_skipped_when_fresh(self) -> None:
        """Symbols sync skipped when cache is fresh."""
        fresh_row = {"fetched_at": "2024-02-04T12:00:00+00:00"}
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = fresh_row
        mock_rates_repo.cache_ttl_seconds = 86400

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = fresh_row
        mock_symbols_repo.cache_ttl_seconds = 86400

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods (used by sync_all_rates)
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        assert result["providers"]["symbols"]["skipped"] == "fresh-cache"
        mock_symbols_repo.store_symbols.assert_not_called()

    def test_force_with_no_provider_data(self) -> None:
        """Handles case when force=True but all providers return None."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None
        mock_symbols_repo.store_symbols.return_value = "test-symbols-id"

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        # All providers return None
        mock_provider_service.fetch_fixer.return_value = None
        mock_provider_service.fetch_frankfurter.return_value = None
        mock_provider_service.fetch_fixer_symbols.return_value = {
            "provider": "fixer",
            "symbols": {"USD": "US Dollar"},
        }

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=True)

        # No combined rates should be created since no provider returned data
        # But combined should not have skipped status since force=True
        assert "combined" not in result["providers"] or "run_id" not in result["providers"].get(
            "combined", {}
        )

    def test_symbols_sync_error(self) -> None:
        """Handles exception during symbols sync gracefully."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        mock_provider_service.fetch_fixer.return_value = {
            "provider": "fixer",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.08},
        }
        mock_provider_service.fetch_frankfurter.return_value = None
        # Symbols fetch raises exception
        mock_provider_service.fetch_fixer_symbols.side_effect = RuntimeError("Symbols API error")

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        # Symbols should have error, but rates should succeed
        assert "error" in result["providers"]["symbols"]
        assert "run_id" in result["providers"]["fixer"]

    def test_symbols_returns_none(self) -> None:
        """Handles when fetch_fixer_symbols returns None (no API key)."""
        mock_rates_repo = MagicMock()
        mock_rates_repo.get_latest_run_if_fresh.return_value = None
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.get_latest_if_fresh.return_value = None

        mock_provider_service = MagicMock()
        # Set __name__ attributes for the fetcher methods
        mock_provider_service.fetch_fixer.__name__ = "fetch_fixer"
        mock_provider_service.fetch_frankfurter.__name__ = "fetch_frankfurter"
        mock_provider_service.fetch_fixer.return_value = {
            "provider": "fixer",
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.08},
        }
        mock_provider_service.fetch_frankfurter.return_value = None
        # Symbols fetch returns None (e.g., no API key configured)
        mock_provider_service.fetch_fixer_symbols.return_value = None

        service = RatesSyncService(
            rates_repo=mock_rates_repo,
            symbols_repo=mock_symbols_repo,
            provider_service=mock_provider_service,
            provider_priority=["fixer", "frankfurter"],
        )

        with patch("app.services.rates_sync.httpx.Client"):
            result = service.sync_all_rates(force=False)

        # Symbols should not have run_id or error (just silently skipped)
        assert "symbols" not in result["providers"] or "run_id" not in result["providers"].get(
            "symbols", {}
        )
        # Rates should still succeed
        assert "run_id" in result["providers"]["fixer"]


class TestFmtDuration:
    """Tests for the module-level _fmt_duration helper."""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0.0, "0m"),
            (0, "0m"),
            (45, "0m"),
            (59, "0m"),
            (60, "1m"),
            (119, "1m"),
            (120, "2m"),
            (3540, "59m"),
            (3599, "59m"),
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (3661, "1h 1m"),
            (7384, "2h 3m"),
            (86400, "24h 0m"),
        ],
        ids=[
            "zero-float",
            "zero-int",
            "sub-minute-45s",
            "sub-minute-59s",
            "exactly-one-minute",
            "one-minute-boundary",
            "two-minutes",
            "fifty-nine-minutes",
            "just-under-one-hour",
            "exactly-one-hour",
            "one-hour-one-minute",
            "one-hour-one-minute-one-second",
            "two-hours-three-minutes-four-seconds",
            "twenty-four-hours",
        ],
    )
    def test_format_values(self, seconds: float, expected: str) -> None:
        """Verifies correct hours/minutes formatting for various durations."""
        assert _fmt_duration(seconds) == expected

    def test_negative_clamped_to_zero(self) -> None:
        """Negative seconds are clamped to 0, producing '0m'."""
        assert _fmt_duration(-1) == "0m"
        assert _fmt_duration(-100) == "0m"
        assert _fmt_duration(-999_999) == "0m"

    def test_fractional_seconds_truncated(self) -> None:
        """Fractional seconds are truncated via int(), not rounded."""
        # 119.9 -> int(119) -> 119 // 60 = 1 minute
        assert _fmt_duration(119.9) == "1m"
        # 59.9 -> int(59) -> 59 // 60 = 0 minutes
        assert _fmt_duration(59.9) == "0m"

    def test_hours_shown_only_when_positive(self) -> None:
        """Hours portion is omitted when total duration is under one hour."""
        result_under = _fmt_duration(3599)
        assert "h" not in result_under

        result_at = _fmt_duration(3600)
        assert "h" in result_at


class TestCacheAgeInfo:
    """Tests for RatesSyncService._cache_age_info instance method."""

    @staticmethod
    def _make_service() -> RatesSyncService:
        """Build a minimal RatesSyncService with mock dependencies."""
        return RatesSyncService(
            rates_repo=MagicMock(),
            symbols_repo=MagicMock(),
            provider_service=MagicMock(),
            provider_priority=["fixer"],
        )

    def test_utc_aware_timestamp(self) -> None:
        """UTC-aware ISO timestamp produces correct age and expiry strings."""
        frozen_now = datetime(2025, 6, 15, 14, 0, 0, tzinfo=UTC)
        fetched_at = (frozen_now - timedelta(hours=2)).isoformat()
        ttl_seconds = 24 * 3600  # 24 hours

        with patch("app.services.rates_sync.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = self._make_service()._cache_age_info(fetched_at, ttl_seconds)

        assert result == "fetched 2h 0m ago, expires in 22h 0m"

    def test_naive_timestamp_treated_as_utc(self) -> None:
        """Naive ISO timestamp (no tzinfo) is treated as UTC."""
        frozen_now = datetime(2025, 6, 15, 14, 0, 0, tzinfo=UTC)
        # Naive timestamp - no timezone suffix
        fetched_at = "2025-06-15T12:00:00"
        ttl_seconds = 24 * 3600

        with patch("app.services.rates_sync.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = self._make_service()._cache_age_info(fetched_at, ttl_seconds)

        assert result == "fetched 2h 0m ago, expires in 22h 0m"

    def test_z_suffix_timestamp(self) -> None:
        """ISO timestamp with 'Z' suffix parses correctly."""
        frozen_now = datetime(2025, 6, 15, 14, 0, 0, tzinfo=UTC)
        fetched_at = "2025-06-15T10:00:00Z"
        ttl_seconds = 24 * 3600

        with patch("app.services.rates_sync.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = self._make_service()._cache_age_info(fetched_at, ttl_seconds)

        assert result == "fetched 4h 0m ago, expires in 20h 0m"

    def test_expired_cache_shows_zero_remaining(self) -> None:
        """When TTL is exceeded, remaining time is clamped to '0m'."""
        frozen_now = datetime(2025, 6, 15, 14, 0, 0, tzinfo=UTC)
        # Fetched 25 hours ago, but TTL is only 24 hours
        fetched_at = (frozen_now - timedelta(hours=25)).isoformat()
        ttl_seconds = 24 * 3600

        with patch("app.services.rates_sync.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = self._make_service()._cache_age_info(fetched_at, ttl_seconds)

        assert result == "fetched 25h 0m ago, expires in 0m"

    def test_invalid_string_returns_fallback(self) -> None:
        """Unparseable timestamp falls back to 'fetched_at=<raw>'."""
        result = self._make_service()._cache_age_info("not-a-date", 3600)
        assert result == "fetched_at=not-a-date"

    def test_empty_string_returns_fallback(self) -> None:
        """Empty string falls back to 'fetched_at='."""
        result = self._make_service()._cache_age_info("", 3600)
        assert result == "fetched_at="

    def test_sub_minute_age(self) -> None:
        """Cache fetched seconds ago shows '0m' for age."""
        frozen_now = datetime(2025, 6, 15, 14, 0, 0, tzinfo=UTC)
        fetched_at = (frozen_now - timedelta(seconds=30)).isoformat()
        ttl_seconds = 3600

        with patch("app.services.rates_sync.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = self._make_service()._cache_age_info(fetched_at, ttl_seconds)

        assert result == "fetched 0m ago, expires in 59m"

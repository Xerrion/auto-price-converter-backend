"""Tests for RatesSyncService."""

from unittest.mock import MagicMock, patch

from app.services.rates_sync import RatesSyncService


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
        mock_rates_repo = MagicMock()
        mock_rates_repo.is_fresh.return_value = True  # Cache is fresh

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = True

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
        mock_rates_repo.is_fresh.return_value = True  # Cache is fresh
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = True
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
        mock_rates_repo.is_fresh.return_value = False
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = False
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
        mock_rates_repo.is_fresh.return_value = False
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = False
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
        mock_rates_repo.is_fresh.return_value = False
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = False
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
        mock_rates_repo = MagicMock()
        mock_rates_repo.is_fresh.return_value = True

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = True  # Symbols are fresh

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
        mock_rates_repo.is_fresh.return_value = False
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = False
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
        mock_rates_repo.is_fresh.return_value = False
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = False

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
        mock_rates_repo.is_fresh.return_value = False
        mock_rates_repo.store_run.return_value = "test-run-id"

        mock_symbols_repo = MagicMock()
        mock_symbols_repo.is_fresh.return_value = False

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

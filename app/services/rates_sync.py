"""Service for synchronizing exchange rates from multiple providers."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import httpx

from app.repositories.rates import RatesRepository
from app.repositories.symbols import SymbolsRepository
from app.services.providers import ProviderService

logger = logging.getLogger(__name__)


def _fmt_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds (negative values treated as 0)

    Returns:
        Formatted string like "2h 14m" or "45m" (hours omitted when < 60m)
    """
    total_minutes = max(0, int(seconds)) // 60
    hours, minutes = divmod(total_minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class RatesSyncService:
    """Service for synchronizing exchange rates."""

    def __init__(
        self,
        rates_repo: RatesRepository,
        symbols_repo: SymbolsRepository,
        provider_service: ProviderService,
        provider_priority: list[str],
    ):
        """
        Initialize rates sync service.

        Args:
            rates_repo: Repository for rates database operations
            symbols_repo: Repository for symbols database operations
            provider_service: Service for fetching from external providers
            provider_priority: List of provider names in priority order
        """
        self.rates_repo: RatesRepository = rates_repo
        self.symbols_repo: SymbolsRepository = symbols_repo
        self.provider_service: ProviderService = provider_service
        self.provider_priority: list[str] = provider_priority
        logger.debug(f"Initialized RatesSyncService with priority={provider_priority}")

    def _cache_age_info(self, fetched_at_str: str, ttl_seconds: int) -> str:
        """
        Build a human-readable cache age summary.

        Args:
            fetched_at_str: ISO 8601 timestamp of last fetch
            ttl_seconds: Cache TTL in seconds

        Returns:
            String like "fetched 2h 14m ago, expires in 21h 46m"
        """
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=UTC)
            age_seconds = (datetime.now(UTC) - fetched_at).total_seconds()
            remaining_seconds = ttl_seconds - age_seconds
            age_str = _fmt_duration(age_seconds)
            remaining_str = _fmt_duration(remaining_seconds)
            return f"fetched {age_str} ago, expires in {remaining_str}"
        except (ValueError, TypeError):
            return f"fetched_at={fetched_at_str}"

    def merge_rates(
        self, provider_rates: dict[str, dict[str, float]], priority: list[str]
    ) -> dict[str, float]:
        """
        Merge rates from multiple providers based on priority.

        Args:
            provider_rates: Dictionary mapping provider names to their rates
            priority: List of provider names in priority order

        Returns:
            Merged rates dictionary with EUR always set to 1.0
        """
        logger.debug(f"Merging rates from {len(provider_rates)} providers")
        merged: dict[str, float] = {"EUR": 1.0}

        for provider in priority:
            rates = provider_rates.get(provider)
            if not rates:
                continue
            num_added = 0
            for code, rate in rates.items():
                if code not in merged:
                    merged[code] = rate
                    num_added += 1
            logger.debug(f"Added {num_added} unique rates from provider={provider}")

        logger.info(f"Merged rates complete: total_currencies={len(merged)}")
        return merged

    def sync_all_rates(self, force: bool = False) -> dict[str, object]:
        """
        Sync rates from all providers.

        Args:
            force: If True, skip freshness check and fetch regardless

        Returns:
            Dictionary with sync results for each provider
        """
        logger.info(f"Starting sync_all_rates: force={force}")
        provider_results: dict[str, object] = {}
        provider_rates: dict[str, dict[str, float]] = {}
        provider_dates: dict[str, str] = {}

        fetchers: list[Callable[[httpx.Client], dict[str, object] | None]] = [
            self.provider_service.fetch_fixer,
            self.provider_service.fetch_frankfurter,
        ]

        # Fetch rates from each provider
        with httpx.Client(timeout=20) as client:
            for fetcher in fetchers:
                try:
                    provider_name = fetcher.__name__.replace("fetch_", "")

                    fresh_row = (
                        None if force else self.rates_repo.get_latest_run_if_fresh(provider_name)
                    )
                    if fresh_row is not None:
                        age_info = self._cache_age_info(
                            str(fresh_row["fetched_at"]),
                            self.rates_repo.cache_ttl_seconds,
                        )
                        logger.info(f"Skipping {provider_name}: cache is fresh ({age_info})")
                        provider_results[provider_name] = {
                            "skipped": "fresh-cache",
                        }
                        continue

                    logger.info(f"Syncing rates from {provider_name}")
                    result = fetcher(client)
                    if not result:
                        logger.warning(f"No result from {provider_name}")
                        continue

                    result_provider = str(result["provider"])
                    result_base = str(result["base"])
                    result_date = str(result["date"])
                    result_rates = cast(dict[str, float], result["rates"])

                    run_id = self.rates_repo.store_run(
                        result_provider,
                        result_base,
                        result_date,
                        result_rates,
                    )
                    logger.info(
                        f"Successfully synced {provider_name}: "
                        + f"run_id={run_id}, num_rates={len(result_rates)}"
                    )
                    provider_results[result_provider] = {"run_id": run_id}
                    provider_rates[result_provider] = result_rates
                    provider_dates[result_provider] = result_date
                except Exception as exc:
                    fetcher_name = getattr(fetcher, "__name__", "unknown")
                    logger.error(f"Error syncing {fetcher_name}: {exc}", exc_info=True)
                    provider_results[str(fetcher_name)] = {"error": str(exc)}

        # Create combined rates run
        if provider_rates:
            logger.info("Creating combined rates from all providers")
            merged_rates = self.merge_rates(provider_rates, self.provider_priority)
            merged_date = max(provider_dates.values())
            combined_run_id = self.rates_repo.store_run(
                "combined", "EUR", merged_date, merged_rates
            )
            logger.info(f"Combined rates created: run_id={combined_run_id}")
            provider_results["combined"] = {"run_id": combined_run_id}
        elif not force:
            fresh_row = self.rates_repo.get_latest_run_if_fresh("combined")
            age_info = (
                self._cache_age_info(
                    str(fresh_row["fetched_at"]),
                    self.rates_repo.cache_ttl_seconds,
                )
                if fresh_row
                else "no cache info"
            )
            logger.info(f"Skipping combined: cache is fresh ({age_info})")
            provider_results["combined"] = {"skipped": "fresh-cache"}
        else:
            logger.warning("No provider rates available for combining")

        # Sync symbols
        fresh_sym = None if force else self.symbols_repo.get_latest_if_fresh("fixer")
        if fresh_sym is None:
            logger.info("Syncing currency symbols")
            with httpx.Client(timeout=20) as client:
                try:
                    symbols_result = self.provider_service.fetch_fixer_symbols(client)
                    if symbols_result:
                        symbols_provider = str(symbols_result["provider"])
                        symbols_data = cast(dict[str, str], symbols_result["symbols"])
                        symbols_run_id = self.symbols_repo.store_symbols(
                            symbols_provider,
                            symbols_data,
                        )
                        logger.info(f"Symbols synced: run_id={symbols_run_id}")
                        provider_results["symbols"] = {"run_id": symbols_run_id}
                    else:
                        logger.warning("No symbols returned from Fixer")
                except Exception as exc:
                    logger.error(f"Error syncing symbols: {exc}", exc_info=True)
                    provider_results["symbols"] = {"error": str(exc)}
        else:
            age_info = self._cache_age_info(
                str(fresh_sym["fetched_at"]),
                self.symbols_repo.cache_ttl_seconds,
            )
            logger.info(f"Skipping symbols: cache is fresh ({age_info})")
            provider_results["symbols"] = {"skipped": "fresh-cache"}

        logger.info(f"Sync complete: {len(provider_results)} results")
        return {"providers": provider_results}

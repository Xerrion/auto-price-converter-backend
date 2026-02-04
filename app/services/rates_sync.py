"""Service for synchronizing exchange rates from multiple providers."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RatesSyncService:
    """Service for synchronizing exchange rates."""

    def __init__(
        self,
        rates_repo: Any,  # Will be properly typed once we create the repository
        symbols_repo: Any,
        provider_service: Any,
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
        self.rates_repo = rates_repo
        self.symbols_repo = symbols_repo
        self.provider_service = provider_service
        self.provider_priority = provider_priority
        logger.debug(f"Initialized RatesSyncService with priority={provider_priority}")

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

    def sync_all_rates(self, force: bool = False) -> dict[str, Any]:
        """
        Sync rates from all providers.

        Args:
            force: If True, skip freshness check and fetch regardless

        Returns:
            Dictionary with sync results for each provider
        """
        logger.info(f"Starting sync_all_rates: force={force}")
        provider_results: dict[str, Any] = {}
        provider_rates: dict[str, dict[str, float]] = {}
        provider_dates: dict[str, str] = {}

        # Fetch rates from each provider
        with httpx.Client(timeout=20) as client:
            for fetcher in [
                self.provider_service.fetch_fixer,
                self.provider_service.fetch_frankfurter,
            ]:
                try:
                    provider_name = fetcher.__name__.replace("fetch_", "")

                    if not force and self.rates_repo.is_fresh(provider_name):
                        logger.info(f"Skipping {provider_name}: cache is fresh")
                        provider_results[provider_name] = {"skipped": "fresh-cache"}
                        continue

                    logger.info(f"Syncing rates from {provider_name}")
                    result = fetcher(client)
                    if not result:
                        logger.warning(f"No result from {provider_name}")
                        continue

                    run_id = self.rates_repo.store_run(
                        result["provider"],
                        result["base"],
                        result["date"],
                        result["rates"],
                    )
                    logger.info(
                        f"Successfully synced {provider_name}: "
                        f"run_id={run_id}, num_rates={len(result['rates'])}"
                    )
                    provider_results[result["provider"]] = {"run_id": run_id}
                    provider_rates[result["provider"]] = result["rates"]
                    provider_dates[result["provider"]] = result["date"]
                except Exception as exc:
                    provider_name = getattr(fetcher, "__name__", "unknown")
                    logger.error(f"Error syncing {provider_name}: {exc}", exc_info=True)
                    provider_results[provider_name] = {"error": str(exc)}

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
            logger.info("No new rates fetched, combined rates skipped")
            provider_results["combined"] = {"skipped": "fresh-cache"}
        else:
            logger.warning("No provider rates available for combining")

        # Sync symbols
        if force or not self.symbols_repo.is_fresh("fixer"):
            logger.info("Syncing currency symbols")
            with httpx.Client(timeout=20) as client:
                try:
                    symbols_result = self.provider_service.fetch_fixer_symbols(client)
                    if symbols_result:
                        symbols_run_id = self.symbols_repo.store_symbols(
                            symbols_result["provider"],
                            symbols_result["symbols"],
                        )
                        logger.info(f"Symbols synced: run_id={symbols_run_id}")
                        provider_results["symbols"] = {"run_id": symbols_run_id}
                    else:
                        logger.warning("No symbols returned from Fixer")
                except Exception as exc:
                    logger.error(f"Error syncing symbols: {exc}", exc_info=True)
                    provider_results["symbols"] = {"error": str(exc)}
        else:
            logger.info("Skipping symbols sync: cache is fresh")
            provider_results["symbols"] = {"skipped": "fresh-cache"}

        logger.info(f"Sync complete: {len(provider_results)} results")
        return {"providers": provider_results}

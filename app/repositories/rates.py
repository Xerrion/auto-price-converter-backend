"""Repository for rates database operations."""

import logging
from datetime import UTC, datetime

from supabase import Client

logger = logging.getLogger(__name__)


class RatesRepository:
    """Repository for rates database operations."""

    def __init__(self, supabase: Client, cache_ttl_seconds: int):
        """
        Initialize rates repository.

        Args:
            supabase: Supabase client for database operations
            cache_ttl_seconds: Cache TTL in seconds for freshness checks
        """
        self.supabase = supabase
        self.cache_ttl_seconds = cache_ttl_seconds
        logger.debug(f"Initialized RatesRepository with cache_ttl={cache_ttl_seconds}s")

    def store_run(self, provider: str, base: str, date: str, rates: dict[str, float]) -> str:
        """
        Store a rates run and its entries.

        Args:
            provider: Provider name (e.g., "fixer", "frankfurter", "combined")
            base: Base currency code
            date: Date string for the rates
            rates: Dictionary of currency codes to rates

        Returns:
            The run_id of the created rates run

        Raises:
            RuntimeError: If database insert fails
        """
        logger.info(
            f"Storing rates run: provider={provider}, base={base}, date={date}, "
            f"num_rates={len(rates)}"
        )

        run_payload = {
            "provider": provider,
            "base": base,
            "date": date,
            "fetched_at": datetime.now(tz=UTC).isoformat(),
        }
        run_resp = self.supabase.table("rates_runs").insert(run_payload).execute()
        if not run_resp.data:
            logger.error(f"Failed to insert rates run for provider={provider}")
            raise RuntimeError("Failed to insert rates run")

        run_id = run_resp.data[0]["id"]
        logger.debug(f"Created rates run with id={run_id}")

        entries_payload = [
            {"run_id": run_id, "currency": code, "rate": float(rate)}
            for code, rate in rates.items()
        ]
        if entries_payload:
            self.supabase.table("rates_entries").insert(entries_payload).execute()
            logger.debug(f"Stored {len(entries_payload)} rate entries for run_id={run_id}")

        logger.info(f"Successfully stored rates run: run_id={run_id}, provider={provider}")
        return run_id

    def get_latest_run(self, provider: str) -> dict | None:
        """
        Get latest rates run for a provider.

        Args:
            provider: Provider name to query

        Returns:
            Dictionary with provider, base, date, fetched_at, and rates, or None if not found
        """
        logger.debug(f"Fetching latest run for provider={provider}")

        run_resp = (
            self.supabase.table("latest_rates")
            .select("provider, base, date, fetched_at, rates")
            .eq("provider", provider)
            .limit(1)
            .execute()
        )
        if not run_resp.data:
            logger.debug(f"No rates found for provider={provider}")
            return None

        run = run_resp.data[0]
        rates = {code: float(rate) for code, rate in (run.get("rates") or {}).items()}
        result = {
            "provider": run["provider"],
            "base": run["base"],
            "date": str(run["date"]),
            "fetched_at": str(run["fetched_at"]),
            "rates": rates,
        }

        logger.debug(
            f"Retrieved latest run for provider={provider}: "
            f"date={result['date']}, num_rates={len(rates)}"
        )
        return result

    def is_fresh(self, provider: str) -> bool:
        """
        Check if provider's rates are still fresh.

        Args:
            provider: Provider name to check

        Returns:
            True if rates are still within the cache TTL window
        """
        latest = self.get_latest_run(provider)
        if not latest:
            logger.debug(f"No cached data for provider={provider}")
            return False

        try:
            fetched_at = datetime.fromisoformat(latest["fetched_at"])
        except ValueError:
            logger.warning(f"Invalid timestamp for provider={provider}")
            return False

        now = datetime.now(tz=UTC)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)

        age_seconds = (now - fetched_at).total_seconds()
        is_fresh = age_seconds < self.cache_ttl_seconds

        logger.debug(
            f"Freshness check for provider={provider}: "
            f"age={age_seconds:.0f}s, ttl={self.cache_ttl_seconds}s, fresh={is_fresh}"
        )
        return is_fresh

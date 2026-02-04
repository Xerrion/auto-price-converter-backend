"""Repository for symbols database operations."""

import logging
from datetime import UTC, datetime

from supabase import Client

logger = logging.getLogger(__name__)


class SymbolsRepository:
    """Repository for symbols database operations."""

    def __init__(self, supabase: Client, cache_ttl_seconds: int):
        """
        Initialize symbols repository.

        Args:
            supabase: Supabase client for database operations
            cache_ttl_seconds: Cache TTL in seconds for freshness checks
        """
        self.supabase = supabase
        self.cache_ttl_seconds = cache_ttl_seconds
        logger.debug(f"Initialized SymbolsRepository with cache_ttl={cache_ttl_seconds}s")

    def store_symbols(self, provider: str, symbols: dict[str, str]) -> str:
        """
        Store a symbols run.

        Args:
            provider: Provider name (e.g., "fixer")
            symbols: Dictionary of currency codes to descriptions

        Returns:
            The run_id of the created symbols run

        Raises:
            RuntimeError: If database insert fails
        """
        logger.info(f"Storing symbols: provider={provider}, num_symbols={len(symbols)}")

        payload = {
            "provider": provider,
            "symbols": symbols,
            "fetched_at": datetime.now(tz=UTC).isoformat(),
        }
        resp = self.supabase.table("symbols_runs").insert(payload).execute()
        if not resp.data:
            logger.error(f"Failed to insert symbols run for provider={provider}")
            raise RuntimeError("Failed to insert symbols run")

        run_id = resp.data[0]["id"]
        logger.info(f"Successfully stored symbols: run_id={run_id}, provider={provider}")
        return run_id

    def get_latest(self, provider: str) -> dict | None:
        """
        Get latest symbols for a provider.

        Args:
            provider: Provider name to query

        Returns:
            Dictionary with provider, fetched_at, and symbols, or None if not found
        """
        logger.debug(f"Fetching latest symbols for provider={provider}")

        symbols_resp = (
            self.supabase.table("latest_symbols")
            .select("provider, fetched_at, symbols")
            .eq("provider", provider)
            .limit(1)
            .execute()
        )
        if not symbols_resp.data:
            logger.debug(f"No symbols found for provider={provider}")
            return None

        row = symbols_resp.data[0]
        symbols = row.get("symbols") or {}
        result = {
            "provider": row["provider"],
            "fetched_at": str(row["fetched_at"]),
            "symbols": symbols,
        }

        logger.debug(f"Retrieved symbols for provider={provider}: num_symbols={len(symbols)}")
        return result

    def is_fresh(self, provider: str) -> bool:
        """
        Check if provider's symbols are still fresh.

        Args:
            provider: Provider name to check

        Returns:
            True if symbols are still within the cache TTL window
        """
        latest = self.get_latest(provider)
        if not latest:
            logger.debug(f"No cached symbols for provider={provider}")
            return False

        try:
            fetched_at = datetime.fromisoformat(latest["fetched_at"])
        except ValueError:
            logger.warning(f"Invalid timestamp for symbols provider={provider}")
            return False

        now = datetime.now(tz=UTC)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)

        age_seconds = (now - fetched_at).total_seconds()
        is_fresh = age_seconds < self.cache_ttl_seconds

        logger.debug(
            f"Freshness check for symbols provider={provider}: "
            f"age={age_seconds:.0f}s, ttl={self.cache_ttl_seconds}s, fresh={is_fresh}"
        )
        return is_fresh

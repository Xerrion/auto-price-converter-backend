"""Service for fetching exchange rates from external providers."""

import logging
from typing import Any

import httpx

from app.services.normalization import normalize_to_eur

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for fetching exchange rates from external providers."""

    def __init__(self, fixer_api_key: str | None = None):
        """
        Initialize provider service.

        Args:
            fixer_api_key: API key for Fixer.io service
        """
        self.fixer_api_key = fixer_api_key
        logger.debug(
            f"Initialized ProviderService with "
            f"fixer_api_key={'set' if fixer_api_key else 'not set'}"
        )

    def fetch_fixer(self, client: httpx.Client) -> dict[str, Any] | None:
        """
        Fetch exchange rates from Fixer API.

        Args:
            client: HTTP client for making requests

        Returns:
            Dictionary with provider, base, date, and normalized rates, or None if no API key

        Raises:
            RuntimeError: If Fixer API returns an error
            httpx.HTTPStatusError: If HTTP request fails
        """
        if not self.fixer_api_key:
            logger.warning("Fixer API key not configured, skipping fetch")
            return None

        logger.info("Fetching rates from Fixer API")
        url = "http://data.fixer.io/api/latest"

        try:
            response = client.get(url, params={"access_key": self.fixer_api_key})
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                error_msg = f"Fixer error: {data.get('error')}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            base = data.get("base", "EUR")
            rates = data.get("rates", {})
            normalized = normalize_to_eur(base, rates)

            logger.info(
                f"Successfully fetched Fixer rates: base={base}, "
                f"date={data.get('date')}, num_rates={len(normalized)}"
            )

            return {
                "provider": "fixer",
                "base": "EUR",
                "date": data.get("date"),
                "rates": normalized,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching from Fixer: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching from Fixer: {e}")
            raise

    def fetch_frankfurter(self, client: httpx.Client) -> dict[str, Any] | None:
        """
        Fetch exchange rates from Frankfurter API.

        Args:
            client: HTTP client for making requests

        Returns:
            Dictionary with provider, base, date, and normalized rates

        Raises:
            httpx.HTTPStatusError: If HTTP request fails
        """
        logger.info("Fetching rates from Frankfurter API")
        url = "https://api.frankfurter.dev/v1/latest"

        try:
            response = client.get(url, params={"base": "EUR"})
            response.raise_for_status()
            data = response.json()
            rates = data.get("rates", {})
            normalized = normalize_to_eur("EUR", rates)

            logger.info(
                f"Successfully fetched Frankfurter rates: "
                f"date={data.get('date')}, num_rates={len(normalized)}"
            )

            return {
                "provider": "frankfurter",
                "base": "EUR",
                "date": data.get("date"),
                "rates": normalized,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching from Frankfurter: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching from Frankfurter: {e}")
            raise

    def fetch_fixer_symbols(self, client: httpx.Client) -> dict[str, Any] | None:
        """
        Fetch currency symbols from Fixer API.

        Args:
            client: HTTP client for making requests

        Returns:
            Dictionary with provider and symbols, or None if no API key

        Raises:
            RuntimeError: If Fixer API returns an error
            httpx.HTTPStatusError: If HTTP request fails
        """
        if not self.fixer_api_key:
            logger.warning("Fixer API key not configured, skipping symbols fetch")
            return None

        logger.info("Fetching currency symbols from Fixer API")
        url = "http://data.fixer.io/api/symbols"

        try:
            response = client.get(url, params={"access_key": self.fixer_api_key})
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                error_msg = f"Fixer symbols error: {data.get('error')}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            symbols = data.get("symbols", {})
            logger.info(f"Successfully fetched Fixer symbols: num_symbols={len(symbols)}")
            return {"provider": "fixer", "symbols": symbols}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching symbols from Fixer: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching symbols from Fixer: {e}")
            raise

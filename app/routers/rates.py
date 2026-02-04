"""Rates router for exchange rates endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import Settings, get_settings
from app.core.deps import RatesRepoDep
from app.utils.caching import apply_cache_headers, build_etag, check_etag_match

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("/latest", response_model=None)
def latest_rates(
    request: Request,
    response: Response,
    rates_repo: RatesRepoDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: str | None = None,
):
    """
    Get latest exchange rates.

    Args:
        response: FastAPI response object for setting headers
        request: FastAPI request object for ETag checking
        provider: Optional provider name (defaults to "combined")
        rates_repo: Rates repository dependency
        settings: Application settings dependency

    Returns:
        Dictionary with base, date, fetched_at, and rates, or 304 Not Modified response

    Raises:
        HTTPException: 404 if no rates are available
    """
    requested = provider or "combined"
    logger.info(f"GET /rates/latest requested: provider={requested}")

    run = rates_repo.get_latest_run(requested)

    # Fallback to individual providers if combined not found
    if not run and requested == "combined":
        logger.debug("Combined rates not found, trying fallback providers")
        for fallback in ["fixer", "frankfurter"]:
            run = rates_repo.get_latest_run(fallback)
            if run:
                logger.info(f"Using fallback provider: {fallback}")
                break

    if not run:
        logger.warning(f"No rates available for provider={requested}")
        raise HTTPException(status_code=404, detail="No rates available")

    payload = {
        "base": run["base"],
        "date": run["date"],
        "fetched_at": run["fetched_at"],
        "rates": run["rates"],
    }

    etag = build_etag(payload)
    if check_etag_match(request, etag):
        logger.debug(f"ETag match, returning 304 Not Modified for provider={requested}")
        not_modified = Response(status_code=304)
        apply_cache_headers(not_modified, etag, settings.cache_ttl_seconds)
        return not_modified

    logger.info(
        f"Returning rates: provider={requested}, date={run['date']}, num_rates={len(run['rates'])}"
    )
    apply_cache_headers(response, etag, settings.cache_ttl_seconds)
    return payload

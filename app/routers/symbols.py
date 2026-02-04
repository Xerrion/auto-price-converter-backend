"""Symbols router for currency symbols endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import Settings, get_settings
from app.core.deps import SymbolsRepoDep
from app.utils.caching import apply_cache_headers, build_etag, check_etag_match

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/symbols", tags=["symbols"])


@router.get("/latest", response_model=None)
def latest_symbols(
    request: Request,
    response: Response,
    symbols_repo: SymbolsRepoDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: str | None = None,
):
    """
    Get latest currency symbols.

    Args:
        response: FastAPI response object for setting headers
        request: FastAPI request object for ETag checking
        provider: Optional provider name (defaults to "fixer")
        symbols_repo: Symbols repository dependency
        settings: Application settings dependency

    Returns:
        Dictionary with provider and symbols, or 304 Not Modified response

    Raises:
        HTTPException: 404 if no symbols are available
    """
    requested = provider or "fixer"
    logger.info(f"GET /symbols/latest requested: provider={requested}")

    result = symbols_repo.get_latest(requested)
    if not result:
        logger.warning(f"No symbols available for provider={requested}")
        raise HTTPException(status_code=404, detail="No symbols available")

    payload = {"provider": result["provider"], "symbols": result["symbols"]}
    etag = build_etag(payload)
    if check_etag_match(request, etag):
        logger.debug(f"ETag match, returning 304 Not Modified for provider={requested}")
        not_modified = Response(status_code=304)
        apply_cache_headers(not_modified, etag, settings.cache_ttl_seconds)
        return not_modified

    logger.info(f"Returning symbols: provider={requested}, num_symbols={len(result['symbols'])}")
    apply_cache_headers(response, etag, settings.cache_ttl_seconds)
    return payload

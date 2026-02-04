"""HTTP caching utilities for ETags and Cache-Control headers."""

import hashlib
import json
from typing import Any

from fastapi import Request, Response


def build_etag(payload: dict[str, Any]) -> str:
    """
    Build ETag from response payload.

    Args:
        payload: Response data to generate ETag from

    Returns:
        ETag string wrapped in quotes
    """
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    return f'"{digest}"'


def apply_cache_headers(response: Response, etag: str, cache_ttl: int) -> None:
    """
    Apply caching headers to response.

    Args:
        response: FastAPI response object to add headers to
        etag: ETag value to set
        cache_ttl: Cache TTL in seconds
    """
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = (
        f"public, max-age={cache_ttl}, s-maxage={cache_ttl}, "
        f"stale-while-revalidate={cache_ttl}, stale-if-error={cache_ttl}"
    )


def check_etag_match(request: Request, etag: str) -> bool:
    """
    Check if request ETag matches current ETag.

    Args:
        request: FastAPI request object
        etag: Current ETag to compare against

    Returns:
        True if ETags match (304 should be returned)
    """
    return request.headers.get("if-none-match") == etag


def create_not_modified_response(etag: str, cache_ttl: int) -> Response:
    """
    Create a 304 Not Modified response.

    Args:
        etag: ETag value to set
        cache_ttl: Cache TTL in seconds

    Returns:
        Response object with 304 status and proper cache headers
    """
    response = Response(status_code=304)
    apply_cache_headers(response, etag, cache_ttl)
    return response

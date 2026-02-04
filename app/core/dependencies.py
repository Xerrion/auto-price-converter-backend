"""Security dependencies and authentication."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings

# Define API key header with auto_error=False to allow optional authentication
# This will show up in Swagger UI with a lock icon
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    x_api_key: Annotated[str | None, Depends(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str | None:
    """
    Verify API key for protected endpoints.

    Args:
        x_api_key: API key from request header
        settings: Application settings

    Returns:
        The API key if valid, or None if no key is required

    Raises:
        HTTPException: 401 if key is required but invalid
    """
    if settings.sync_api_key and x_api_key != settings.sync_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key

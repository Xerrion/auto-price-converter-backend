"""Database models for currency symbols."""

from datetime import datetime

from pydantic import BaseModel


class SymbolsRun(BaseModel):
    """Currency symbols snapshot from a provider."""

    id: str | None = None
    provider: str
    fetched_at: datetime | None = None
    symbols: dict[str, str]


class SymbolsResponse(BaseModel):
    """API response for currency symbols."""

    provider: str
    symbols: dict[str, str]

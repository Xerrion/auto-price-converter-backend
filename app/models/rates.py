"""Database models for exchange rates."""

from datetime import datetime

from pydantic import BaseModel, Field


class RatesEntry(BaseModel):
    """Individual currency rate entry."""

    run_id: str
    currency: str
    rate: float


class RatesRun(BaseModel):
    """Exchange rates snapshot from a provider."""

    id: str | None = None
    provider: str
    base: str
    date: str
    fetched_at: datetime | None = None
    rates: dict[str, float] = Field(default_factory=dict)


class RatesResponse(BaseModel):
    """API response for latest rates."""

    base: str
    date: str
    fetched_at: str
    rates: dict[str, float]

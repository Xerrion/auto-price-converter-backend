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

    base: str = Field(..., description="Base currency code")
    date: str = Field(..., description="Exchange rate date (YYYY-MM-DD)")
    fetched_at: datetime = Field(..., description="Timestamp when rates were fetched")
    rates: dict[str, float] = Field(..., description="Currency exchange rates")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "base": "EUR",
                "date": "2024-02-04",
                "fetched_at": "2024-02-04T12:34:56.789Z",
                "rates": {"USD": 1.0823, "GBP": 0.8543, "JPY": 161.95},
            }
        }

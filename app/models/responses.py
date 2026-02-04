"""API response models for all endpoints."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., example="ok", description="Service status")


class SyncProviderResult(BaseModel):
    """Result for a single provider sync operation."""

    run_id: str | None = Field(default=None, description="Database run ID if sync succeeded")
    skipped: str | None = Field(
        default=None, description="Reason for skipping (e.g., 'fresh-cache')"
    )
    error: str | None = Field(default=None, description="Error message if sync failed")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "examples": [
                {"run_id": "550e8400-e29b-41d4-a716-446655440000"},
                {"skipped": "fresh-cache"},
                {"error": "Connection timeout"},
            ]
        }


class SyncResponse(BaseModel):
    """Response from manual sync job."""

    providers: dict[str, SyncProviderResult] = Field(
        ...,
        description="Sync results for each provider (fixer, frankfurter, combined, symbols)",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "providers": {
                    "fixer": {"run_id": "550e8400-e29b-41d4-a716-446655440000"},
                    "frankfurter": {"run_id": "660e8400-e29b-41d4-a716-446655440001"},
                    "combined": {"run_id": "770e8400-e29b-41d4-a716-446655440002"},
                    "symbols": {"run_id": "880e8400-e29b-41d4-a716-446655440003"},
                }
            }
        }

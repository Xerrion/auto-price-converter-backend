# Agent Development Guide

This document provides coding standards and conventions for AI agents working on the Auto Price Converter Backend.

## Project Overview

FastAPI backend service that fetches exchange rates from multiple providers (Fixer, Frankfurter), stores them in Supabase, and serves a public API with ETag caching. Uses clean layered architecture with dependency injection.

**Tech Stack**: Python 3.9+, FastAPI, Pydantic v2, Supabase, UV package manager

## Documentation Lookup Policy

**CRITICAL**: Always consult official documentation via Context7 tools when:

- Implementing features with FastAPI, Pydantic, Supabase, or other dependencies
- Unsure about API syntax, parameters, or best practices
- Working with unfamiliar library features or patterns
- Encountering errors or unexpected behavior

**Context7 Tools Available**:

1. `Context7_resolve-library-id` - Find the correct library ID (e.g., "fastapi" → "/tiangolo/fastapi")
2. `Context7_query-docs` - Query official docs with specific questions

**Example Usage**:

```text
Question: "How do I add response_model validation in FastAPI?"
1. Resolve: Context7_resolve-library-id(libraryName="fastapi", query="response model validation")
2. Query: Context7_query-docs(libraryId="/tiangolo/fastapi", query="response_model validation examples")
```

**When to Use Context7**:

- ✅ Before implementing new FastAPI routes or middleware
- ✅ When adding Pydantic v2 features (Field validators, computed fields, etc.)
- ✅ For Supabase Python client operations (queries, RLS, auth)
- ✅ When debugging library-specific errors
- ❌ Don't guess library APIs - always verify with official docs first!

## Build & Development Commands

### Setup

```bash
# Install dependencies (recommended)
uv sync

# Alternative: pip install
python -m venv .venv && source .venv/bin/activate && pip install -e .
```

### Running the Server

```bash
# Development with auto-reload
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Linting & Formatting

```bash
# Check all code
uv run ruff check app/

# Auto-fix issues
uv run ruff check app/ --fix

# Format code
uv run ruff format app/

# Fix unsafe issues (like sorting __all__)
uv run ruff check app/ --fix --unsafe-fixes
```

### Testing

The project has a comprehensive test suite with **108 tests** and **89% coverage**.

```bash
# Run all tests
uv run pytest

# Run single test file
uv run pytest tests/test_rates.py

# Run single test function
uv run pytest tests/test_rates.py::test_latest_rates -v

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Run tests in parallel (faster)
uv run pytest -n auto
```

### Database Migrations

```bash
# Create new migration
supabase migration new migration_name

# Apply migrations
supabase db push

# Check migration status
supabase migration list
```

## Architecture

### Directory Structure

```
app/
├── core/          # Config, database, logging, dependencies
├── models/        # Pydantic models (request/response schemas)
├── repositories/  # Database operations (Supabase)
├── routers/       # API endpoints (health, rates, symbols, jobs)
├── services/      # Business logic (providers, sync, normalization)
└── utils/         # Utilities (caching, ETag support)
```

### Layer Responsibilities

- **Routers**: HTTP handling, request/response, ETag caching
- **Services**: Business logic, orchestration, external API calls
- **Repositories**: Database queries, data persistence
- **Models**: Data validation, serialization, OpenAPI schemas
- **Core**: Cross-cutting concerns (config, logging, dependencies)

## Code Style Guidelines

### Imports

Follow this strict order (enforced by ruff isort):

```python
"""Module docstring at the top."""

# 1. Standard library
import logging
from typing import Annotated

# 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# 3. Local application imports
from app.core.config import Settings, get_settings
from app.models import RatesResponse
from app.utils.caching import build_etag
```

### Type Hints

- **Always use type hints** for function parameters and return values
- Use modern Python syntax: `str | None` instead of `Optional[str]`
- Use `dict[str, float]` instead of `Dict[str, float]`
- Use `Annotated` for FastAPI dependencies:

  ```python
  def endpoint(
      settings: Annotated[Settings, Depends(get_settings)],
      api_key: Annotated[str | None, Depends(verify_api_key)],
  ) -> ResponseModel:
  ```

### Naming Conventions

- **Files**: Snake case (`rates_sync.py`, `caching.py`)
- **Classes**: Pascal case (`RatesSyncService`, `RatesResponse`)
- **Functions/Variables**: Snake case (`sync_all_rates`, `provider_priority`)
- **Constants**: Upper snake case (`CACHE_TTL_SECONDS`, `LOG_LEVEL`)
- **Private methods**: Prefix with underscore (`_build_etag`)

### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def merge_rates(
    self, provider_rates: dict[str, dict[str, float]], priority: list[str]
) -> dict[str, float]:
    """
    Merge rates from multiple providers based on priority.

    Args:
        provider_rates: Dictionary mapping provider names to their rates
        priority: List of provider names in priority order

    Returns:
        Merged rates dictionary with EUR always set to 1.0

    Raises:
        ValueError: If provider_rates is empty
    """
```

### Pydantic Models

- Use `BaseModel` for all data models
- Add `Field(...)` with descriptions for OpenAPI documentation
- Use `datetime` types (Pydantic auto-serializes to ISO 8601)
- Add `Config` class with `json_schema_extra` for examples:

  ```python
  class RatesResponse(BaseModel):
      """API response for latest rates."""

      base: str = Field(..., description="Base currency code")
      fetched_at: datetime = Field(..., description="Timestamp when rates were fetched")
      rates: dict[str, float] = Field(..., description="Currency exchange rates")

      class Config:
          json_schema_extra = {
              "example": {
                  "base": "EUR",
                  "fetched_at": "2024-02-04T12:34:56.789Z",
                  "rates": {"USD": 1.0823}
              }
          }
  ```

### FastAPI Routers

- Always specify `response_model` in route decorators
- Use proper return type annotations (including `Response` for 304s)
- Add comprehensive docstrings with Args/Returns/Raises sections
- Use dependency injection for all services/repos
- Return Pydantic model instances, not plain dicts:

  ```python
  @router.get("/latest", response_model=RatesResponse)
  def latest_rates(...) -> RatesResponse | Response:
      """Get latest exchange rates."""
      # Build Pydantic model
      rates_response = RatesResponse(...)
      return rates_response  # Not: return {...}
  ```

### Error Handling

- Use `HTTPException` for API errors with proper status codes
- Log errors with context before raising:

  ```python
  logger.error(f"Failed to sync {provider}: {exc}", exc_info=True)
  raise HTTPException(status_code=500, detail="Sync failed")
  ```

- Use try/except for external API calls (Supabase, Fixer, etc.)
- Never expose internal errors to API clients

### Logging

- Get logger at module level: `logger = logging.getLogger(__name__)`
- Use structured logging with context:

  ```python
  logger.info(f"GET /rates/latest requested: provider={requested}")
  logger.debug(f"Cache hit for provider={provider}")
  logger.error(f"Error syncing {provider}: {exc}", exc_info=True)
  ```

- Levels: `DEBUG` (development), `INFO` (production), `ERROR` (always)

## Important Patterns

### ETag Caching

Always use `model_dump(mode='json')` to serialize Pydantic models for ETags:

```python
rates_response = RatesResponse(...)
etag = build_etag(rates_response.model_dump(mode='json'))  # Not: model_dump()
```

### Configuration

- All config via Pydantic Settings (`app/core/config.py`)
- Never hardcode values - use environment variables
- Access via dependency injection: `settings: Annotated[Settings, Depends(get_settings)]`

### Database Operations

- Use repository pattern for all Supabase queries
- Repositories return plain dicts, routers convert to Pydantic models
- Always use service role key (not anon key) for backend operations

## Deployment Notes

- **Production URL**: `https://apc-api.up.railway.app`
- **Railway CLI**: Use `railway logs` to view production logs
- **GitHub Actions**: Syncs rates daily at 06:00 UTC via cron job
- **Environment**: Required vars in `.env.example`
- **RLS Policies**: Service role has full access, public has read-only

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | (required) | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | (required) | Supabase service role key |
| `FIXER_API_KEY` | `None` | Fixer.io API key |
| `SYNC_API_KEY` | `None` | API key for `/jobs/sync` endpoint |
| `SYNC_INTERVAL_HOURS` | `24` | Exchange rates cache TTL (hours) |
| `SYMBOLS_CACHE_HOURS` | `4320` | Currency symbols cache TTL (hours, 4320 = 180 days) |
| `PROVIDER_PRIORITY` | `fixer,frankfurter` | Provider merge priority |
| `ALLOW_ORIGINS` | `*` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Environment name |

## Common Gotchas

1. **DateTime Serialization**: Use `datetime` type in models, not `str`
2. **ETag with Pydantic**: Always use `model_dump(mode='json')`
3. **Response Models**: Return model instances, not dicts
4. **Import Sorting**: Run `ruff check --fix` to auto-sort imports
5. **Line Length**: Max 100 characters (enforced by ruff)
6. **Python Version**: Target 3.13+ but maintain 3.9+ compatibility

## Git Conventions

- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Commit messages: Imperative mood ("add feature" not "added feature")
- **Atomic commits**: Each commit should touch as few files as possible
- Small, focused commits with clear descriptions
- Always work on feature branches, never commit directly to main
- Always create PRs for code review before merging
- Never commit `.env` files or secrets

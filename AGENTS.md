# AGENTS.md - Coding Agent Guidelines

This file provides essential information for AI coding agents working in this repository.

## Project Overview

**Auto Price Converter Backend** is a FastAPI service that fetches exchange rates from multiple providers (Fixer, Frankfurter), stores them in Supabase, and serves a public API with ETag caching. Uses clean layered architecture with dependency injection.

**Tech Stack**: Python 3.9+, FastAPI, Pydantic v2, Supabase, UV package manager

## Package Manager

⚠️ **ALWAYS use `uv` as the package manager** - It's faster and more reliable than pip.

```bash
uv sync                  # Install dependencies
uv add <package>         # Add a dependency
uv remove <package>      # Remove a dependency
```

**Alternative (pip):**

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e .
```

## Build & Development Commands

### Running the Server

```bash
# Development with auto-reload
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing

The project has a comprehensive test suite with **108 tests** and **89% coverage**.

```bash
uv run pytest                              # Run all tests
uv run pytest tests/test_rates.py          # Run single test file
uv run pytest tests/test_rates.py::test_latest_rates -v  # Run single test function
uv run pytest --cov=app --cov-report=html  # Run with coverage report
uv run pytest -n auto                      # Run tests in parallel (faster)
```

### Linting & Formatting

```bash
uv run ruff check app/              # Check all code
uv run ruff check app/ --fix        # Auto-fix issues
uv run ruff format app/             # Format code
uv run ruff check app/ --fix --unsafe-fixes  # Fix unsafe issues
```

### Database Migrations

```bash
supabase migration new migration_name  # Create new migration
supabase db push                       # Apply migrations
supabase migration list                # Check migration status
```

## Versioning & Releases

This project uses **Release Please** for automated version management and changelog generation.

### How It Works

1. **Make changes** using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add new feature` → Minor version bump
   - `fix: resolve bug` → Patch version bump
   - `feat!: breaking change` or `BREAKING CHANGE:` → Major version bump

2. **Merge to main** → Release Please automatically creates/updates a Release PR with:
   - Version bump in `pyproject.toml`
   - Updated `CHANGELOG.md`

3. **Merge the Release PR** → Automatically:
   - Creates a GitHub Release
   - Creates a git tag

### Configuration Files

- `release-please-config.json` - Release Please configuration
- `.release-please-manifest.json` - Tracks current version

### Required Secret

- `RELEASE_TOKEN` - A GitHub PAT with `contents: write` permission (Fine-grained PAT)

## Project Structure

```text
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

## Documentation Access

⚠️ **ALWAYS consult Context7 documentation when unsure** about library APIs, features, or best practices.

Before implementing features or using unfamiliar APIs:

1. **Query Context7** for the relevant library documentation (FastAPI, Pydantic, Supabase, etc.)
2. **Use `resolve-library-id`** first to get the correct library ID
3. **Use `query-docs`** to get up-to-date API documentation and examples

**Examples of when to use Context7:**

```python
# ❌ Don't guess FastAPI response_model syntax
# ✅ Ask Context7: "How to add response_model validation in FastAPI?"

# ❌ Don't assume Pydantic v2 behavior
# ✅ Ask Context7: "How to use Field validators in Pydantic v2?"

# ❌ Don't guess Supabase Python client
# ✅ Ask Context7: "How to query with filters in Supabase Python?"
```

**This prevents:**

- Using outdated or incorrect API patterns
- Making assumptions about library features
- Missing better approaches that exist in the documentation

## Code Style Guidelines

### General Principles

- **Prefer existing patterns** in `app/` — avoid large refactors
- **Keep changes minimal and focused**
- **Keep functions small and testable**
- Follow the existing code organization and naming conventions

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

- **Files**: snake_case (`rates_sync.py`, `caching.py`)
- **Classes**: PascalCase (`RatesSyncService`, `RatesResponse`)
- **Functions/Variables**: snake_case (`sync_all_rates`, `provider_priority`)
- **Constants**: UPPER_SNAKE_CASE (`CACHE_TTL_SECONDS`, `LOG_LEVEL`)
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
- Add `Config` class with `json_schema_extra` for examples

### FastAPI Routers

- Always specify `response_model` in route decorators
- Use proper return type annotations (including `Response` for 304s)
- Add comprehensive docstrings with Args/Returns/Raises sections
- Use dependency injection for all services/repos
- Return Pydantic model instances, not plain dicts

### Error Handling

- Use `HTTPException` for API errors with proper status codes
- Log errors with context before raising
- Use try/except for external API calls (Supabase, Fixer, etc.)
- Never expose internal errors to API clients

### Logging

- Get logger at module level: `logger = logging.getLogger(__name__)`
- Use structured logging with context
- Levels: `DEBUG` (development), `INFO` (production), `ERROR` (always)

## Common Patterns

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

## Common Issues

1. **DateTime Serialization**: Use `datetime` type in models, not `str`
2. **ETag with Pydantic**: Always use `model_dump(mode='json')`
3. **Response Models**: Return model instances, not dicts
4. **Import Sorting**: Run `ruff check --fix` to auto-sort imports
5. **Line Length**: Max 100 characters (enforced by ruff)
6. **Python Version**: Target 3.13+ but maintain 3.9+ compatibility

## Git Conventions

### Workflow

This project uses a **feature branch** workflow:

1. **Always work on feature branches** — never commit directly to `main`
2. **Always create PRs** for code review before merging
3. **Keep commits atomic** — each commit should touch as few files as possible

### Branch Naming

Use prefixes that match your commit type:

- `feat/` - New features (e.g., `feat/rate-caching`)
- `fix/` - Bug fixes (e.g., `fix/etag-headers`)
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `chore/` - Maintenance tasks

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format (required for Release Please):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat` - New feature (triggers minor version bump)
- `fix` - Bug fix (triggers patch version bump)
- `perf` - Performance improvement
- `refactor` - Code change that neither fixes a bug nor adds a feature
- `docs` - Documentation only
- `chore` - Maintenance tasks
- `test` - Adding or updating tests
- `ci` - CI/CD changes

**Examples:**

```bash
feat: add rate caching endpoint
fix: correct ETag header generation
docs: update API documentation
chore: update dependencies
feat!: redesign sync API  # Breaking change
```

### Pull Requests

- **Update documentation** when behavior changes
- **Add or update tests** when it makes sense
- **Keep PRs narrow and well-scoped**
- Run `uv run ruff check app/` before submitting
- Never commit `.env` files or secrets

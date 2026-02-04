# Backend API

FastAPI service that fetches exchange rates from Fixer and Frankfurter, stores each run in Supabase, and serves a public API for the extension. It also exposes Fixer currency symbols for the extension UI.

## Setup

1. Create the tables in Supabase using `sql/schema.sql`.
2. Copy `.env.example` to `.env` and fill in your secrets.
3. Install dependencies:

   ### Using uv (recommended)
   ```bash
   uv sync
   ```

   ### Using pip
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

4. Run the API:

   ### Using uv
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

   ### Using standard Python
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## API

- `GET /health` - Health check
- `GET /rates/latest` - Returns EUR-based rates (with ETag caching)
- `GET /symbols/latest` - Returns Fixer currency symbols (with ETag caching)
- `POST /jobs/sync` - Protected by `SYNC_API_KEY` header `X-API-Key`

## Configuration

All configuration is managed via environment variables in `.env`:

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `FIXER_API_KEY` - API key for Fixer.io (optional)
- `SYNC_API_KEY` - API key to protect the /jobs/sync endpoint
- `ENABLE_SCHEDULER` - Enable automatic syncing (default: `true`)
- `SYNC_INTERVAL_HOURS` - Hours between automatic syncs (default: `24`)
- `PROVIDER_PRIORITY` - Comma-separated provider priority (default: `fixer,frankfurter`)
- `ALLOW_ORIGINS` - CORS allowed origins (default: `*`)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)
- `ENVIRONMENT` - Environment name: development, production (default: `development`)

## Scheduler

The service can sync every N hours when `ENABLE_SCHEDULER=true`. Set the interval with `SYNC_INTERVAL_HOURS`.

## Logging

The application includes comprehensive structured logging:

- **INFO level** (production): Key operations and API requests
- **DEBUG level** (development): Detailed initialization and cache behavior
- **ERROR level**: Errors with stack traces

Set `LOG_LEVEL=DEBUG` in `.env` for detailed troubleshooting.

## Development

### Running with auto-reload
```bash
uv run uvicorn app.main:app --reload
```

### Code quality
```bash
# Lint code
ruff check app/

# Format code
ruff format app/

# Fix linting issues automatically
ruff check app/ --fix
```

## Notes

- The extension should call the backend only (not the upstream providers).
- Set `VITE_RATES_API_BASE` in the extension environment to your backend base URL.
- The API implements ETag-based caching for efficient bandwidth usage.

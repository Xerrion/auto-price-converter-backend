"""Shared fixtures for all tests."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.repositories.rates import RatesRepository
from app.repositories.symbols import SymbolsRepository
from app.routers import health, jobs, rates, symbols
from app.services.providers import ProviderService
from app.services.rates_sync import RatesSyncService

# -----------------------------------------------------------------------------
# Sample Data Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def sample_rates() -> dict[str, float]:
    """Sample exchange rates."""
    return {
        "EUR": 1.0,
        "USD": 1.0823,
        "GBP": 0.8543,
        "JPY": 161.95,
        "CHF": 0.9412,
    }


@pytest.fixture
def sample_rates_run(sample_rates: dict[str, float]) -> dict:
    """Sample rates run from repository."""
    return {
        "provider": "combined",
        "base": "EUR",
        "date": "2024-02-04",
        "fetched_at": "2024-02-04T12:34:56.789000+00:00",
        "rates": sample_rates,
    }


@pytest.fixture
def sample_symbols() -> dict[str, str]:
    """Sample currency symbols."""
    return {
        "EUR": "Euro",
        "USD": "United States Dollar",
        "GBP": "British Pound Sterling",
        "JPY": "Japanese Yen",
    }


@pytest.fixture
def sample_symbols_run(sample_symbols: dict[str, str]) -> dict:
    """Sample symbols run from repository."""
    return {
        "provider": "fixer",
        "fetched_at": "2024-02-04T12:34:56.789000+00:00",
        "symbols": sample_symbols,
    }


# -----------------------------------------------------------------------------
# Mock Settings
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_service_role_key="test-service-role-key",
        fixer_api_key="test-fixer-key",
        sync_api_key="test-sync-key",
        sync_interval_hours=24,
        provider_priority="fixer,frankfurter",
        allow_origins="*",
        log_level="DEBUG",
        environment="test",
    )


# -----------------------------------------------------------------------------
# Mock Repositories
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_rates_repo(sample_rates_run: dict) -> MagicMock:
    """Create mock rates repository."""
    repo = MagicMock(spec=RatesRepository)
    repo.get_latest_run.return_value = sample_rates_run
    repo.is_fresh.return_value = False
    repo.store_run.return_value = "test-run-id"
    repo.cache_ttl_seconds = 86400
    return repo


@pytest.fixture
def mock_symbols_repo(sample_symbols_run: dict) -> MagicMock:
    """Create mock symbols repository."""
    repo = MagicMock(spec=SymbolsRepository)
    repo.get_latest.return_value = sample_symbols_run
    repo.is_fresh.return_value = False
    repo.store_symbols.return_value = "test-symbols-id"
    repo.cache_ttl_seconds = 86400
    return repo


# -----------------------------------------------------------------------------
# Mock Services
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_provider_service() -> MagicMock:
    """Create mock provider service."""
    service = MagicMock(spec=ProviderService)
    service.fixer_api_key = "test-fixer-key"

    service.fetch_fixer.return_value = {
        "provider": "fixer",
        "base": "EUR",
        "date": "2024-02-04",
        "rates": {"EUR": 1.0, "USD": 1.0823, "GBP": 0.8543},
    }

    service.fetch_frankfurter.return_value = {
        "provider": "frankfurter",
        "base": "EUR",
        "date": "2024-02-04",
        "rates": {"EUR": 1.0, "USD": 1.0820, "JPY": 161.95},
    }

    service.fetch_fixer_symbols.return_value = {
        "provider": "fixer",
        "symbols": {"EUR": "Euro", "USD": "US Dollar"},
    }

    return service


@pytest.fixture
def mock_sync_service(
    mock_rates_repo: MagicMock,
    mock_symbols_repo: MagicMock,
    mock_provider_service: MagicMock,
) -> MagicMock:
    """Create mock sync service."""
    service = MagicMock(spec=RatesSyncService)
    service.sync_all_rates.return_value = {
        "providers": {
            "fixer": {"run_id": "fixer-run-id"},
            "frankfurter": {"run_id": "frankfurter-run-id"},
            "combined": {"run_id": "combined-run-id"},
            "symbols": {"run_id": "symbols-run-id"},
        }
    }
    return service


# -----------------------------------------------------------------------------
# Test Application & Client
# -----------------------------------------------------------------------------


def create_test_app(
    rates_repo: MagicMock,
    symbols_repo: MagicMock,
    sync_service: MagicMock,
    settings: Settings,
) -> FastAPI:
    """Create a test FastAPI application with mocked dependencies."""
    app = FastAPI()

    # Store mocked dependencies in app state
    app.state.rates_repo = rates_repo
    app.state.symbols_repo = symbols_repo
    app.state.sync_service = sync_service

    # Override settings dependency
    from app.core.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings

    # Include routers
    app.include_router(health.router)
    app.include_router(rates.router)
    app.include_router(symbols.router)
    app.include_router(jobs.router)

    return app


@pytest.fixture
def test_app(
    mock_rates_repo: MagicMock,
    mock_symbols_repo: MagicMock,
    mock_sync_service: MagicMock,
    mock_settings: Settings,
) -> FastAPI:
    """Create test FastAPI application."""
    return create_test_app(
        rates_repo=mock_rates_repo,
        symbols_repo=mock_symbols_repo,
        sync_service=mock_sync_service,
        settings=mock_settings,
    )


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


# -----------------------------------------------------------------------------
# Helper Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def fresh_timestamp() -> str:
    """Return a fresh timestamp (within cache TTL)."""
    return datetime.now(tz=UTC).isoformat()


@pytest.fixture
def stale_timestamp() -> str:
    """Return a stale timestamp (outside cache TTL)."""
    from datetime import timedelta

    stale_time = datetime.now(tz=UTC) - timedelta(hours=25)
    return stale_time.isoformat()

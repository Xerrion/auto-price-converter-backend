"""Main FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.core.logging import setup_logging
from app.repositories.rates import RatesRepository
from app.repositories.symbols import SymbolsRepository
from app.routers import health, jobs, rates, symbols
from app.services.providers import ProviderService
from app.services.rates_sync import RatesSyncService

# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    logger.info("Creating FastAPI application")

    # Initialize settings
    settings = get_settings()
    logger.info(
        f"Settings loaded: environment={settings.environment}, "
        f"log_level={settings.log_level}"
    )

    # Create FastAPI app with security scheme for Swagger UI
    app = FastAPI(
        title="Auto Price Converter Rates API",
        swagger_ui_parameters={"persistAuthorization": True},
        servers=[
            {"url": "http://127.0.0.1:8000", "description": "Local development"},
            {"url": "http://localhost:8000", "description": "Local development (localhost)"},
        ],
    )

    # Configure CORS
    origins = settings.origins_list or ["*"]
    logger.info(f"Configuring CORS with origins: {origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize core dependencies
    logger.info("Initializing core dependencies")
    supabase = get_supabase_client()
    rates_repo = RatesRepository(supabase, settings.cache_ttl_seconds)
    symbols_repo = SymbolsRepository(supabase, settings.cache_ttl_seconds)
    provider_service = ProviderService(settings.fixer_api_key)
    sync_service = RatesSyncService(
        rates_repo, symbols_repo, provider_service, settings.provider_priority_list
    )

    # Store dependencies in app state for lifespan and dependency injection
    app.state.settings = settings
    app.state.sync_service = sync_service
    app.state.rates_repo = rates_repo
    app.state.symbols_repo = symbols_repo

    # Dependency overrides for router injection
    def get_rates_repo() -> RatesRepository:
        return app.state.rates_repo

    def get_symbols_repo() -> SymbolsRepository:
        return app.state.symbols_repo

    def get_sync_service() -> RatesSyncService:
        return app.state.sync_service

    # Override dependencies
    app.dependency_overrides[RatesRepository] = get_rates_repo
    app.dependency_overrides[SymbolsRepository] = get_symbols_repo
    app.dependency_overrides[RatesSyncService] = get_sync_service

    # Register routers
    logger.info("Registering API routers")
    app.include_router(health.router)
    app.include_router(rates.router)
    app.include_router(symbols.router)
    app.include_router(jobs.router)

    logger.info("FastAPI application created successfully")
    return app


# Create the app instance
logger.info("Initializing application")
app = create_app()
logger.info("Application ready to serve requests")

"""Common dependencies for the application."""

from typing import Annotated

from fastapi import Depends, Request

from app.repositories.rates import RatesRepository
from app.repositories.symbols import SymbolsRepository
from app.services.rates_sync import RatesSyncService


def get_rates_repo(request: Request) -> RatesRepository:
    """Get rates repository from app state."""
    return request.app.state.rates_repo


def get_symbols_repo(request: Request) -> SymbolsRepository:
    """Get symbols repository from app state."""
    return request.app.state.symbols_repo


def get_sync_service(request: Request) -> RatesSyncService:
    """Get sync service from app state."""
    return request.app.state.sync_service


# Type aliases for easy dependency injection
RatesRepoDep = Annotated[RatesRepository, Depends(get_rates_repo)]
SymbolsRepoDep = Annotated[SymbolsRepository, Depends(get_symbols_repo)]
SyncServiceDep = Annotated[RatesSyncService, Depends(get_sync_service)]

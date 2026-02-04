"""Scheduler management with modern lifespan pattern."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.

    This replaces the deprecated @app.on_event("startup") and
    @app.on_event("shutdown") decorators with a modern context manager approach.

    Args:
        app: FastAPI application instance
    """
    # Startup: Initialize scheduler
    settings = app.state.settings
    scheduler = None

    if settings.enable_scheduler:
        logger.info(f"Starting scheduler: interval={settings.sync_interval_hours}h, enabled=True")
        sync_service = app.state.sync_service
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            sync_service.sync_all_rates, "interval", hours=settings.sync_interval_hours
        )
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Scheduler started successfully")
    else:
        logger.info("Scheduler disabled by configuration")

    yield

    # Shutdown: Cleanup
    if scheduler:
        logger.info("Shutting down scheduler")
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete")

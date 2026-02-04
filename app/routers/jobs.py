"""Jobs router for manual sync endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.core.deps import SyncServiceDep
from app.models import SyncResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/sync", response_model=SyncResponse)
def trigger_sync(
    sync_service: SyncServiceDep,
    api_key: Annotated[str | None, Depends(verify_api_key)],
    force: bool = False,
) -> SyncResponse:
    """
    Trigger manual synchronization of exchange rates.

    Args:
        force: If True, force sync even if data is fresh
        api_key: API key for authentication (injected by dependency)
        sync_service: Rates sync service dependency

    Returns:
        SyncResponse with results for each provider
    """
    logger.info(f"POST /jobs/sync triggered: force={force}")
    result = sync_service.sync_all_rates(force=force)
    logger.info(f"Sync completed: {len(result.get('providers', {}))} provider results")
    return SyncResponse(**result)

"""Jobs router for manual sync endpoints."""

import logging
from typing import Annotated, cast

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.core.deps import SyncServiceDep
from app.models import SyncResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/sync", response_model=SyncResponse)
def trigger_sync(
    sync_service: SyncServiceDep,
    _api_key: Annotated[str | None, Depends(verify_api_key)],
    force: bool = False,
) -> SyncResponse:
    """
    Trigger manual synchronization of exchange rates.

    Args:
        force: If True, force sync even if data is fresh
        _api_key: API key for authentication (injected by dependency)
        sync_service: Rates sync service dependency

    Returns:
        SyncResponse with results for each provider
    """
    logger.info(f"POST /jobs/sync triggered: force={force}")
    result = sync_service.sync_all_rates(force=force)
    providers = cast(dict[str, object], result.get("providers", {}))
    logger.info(f"Sync completed: {len(providers)} provider results")
    return SyncResponse.model_validate(result)

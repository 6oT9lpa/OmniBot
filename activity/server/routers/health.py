from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.activity import ActivityHealthResponse
from activity.server.services.health_service import ActivityHealthService

router = APIRouter()
service = ActivityHealthService()


@router.get("/api/activity/health", response_model=ActivityHealthResponse)
async def get_activity_health(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivityHealthResponse:
    return await service.get_health(str(guild_id), access_token)

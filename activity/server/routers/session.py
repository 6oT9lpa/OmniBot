from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.activity import ActivitySession
from activity.server.services.session_service import ActivitySessionService

router = APIRouter()
service = ActivitySessionService()


@router.get("/api/activity/session", response_model=ActivitySession)
async def get_activity_session(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivitySession:
    return await service.get_session(str(guild_id), access_token)

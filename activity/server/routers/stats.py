from typing import Any

from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.services.stats_service import ActivityStatsService

router = APIRouter()
service = ActivityStatsService()


@router.get("/api/stats/server")
async def get_activity_server_stats(
    guild_id: int = Query(gt=0),
    period: int = Query(default=30, ge=1, le=365),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.get_server_stats(guild_id, period, access_token)


@router.get("/api/stats/users/search")
async def search_activity_user_stats(
    guild_id: int = Query(gt=0),
    q: str = Query(default="", max_length=100),
    access_token: str = Depends(require_bearer_token),
) -> list[dict[str, Any]]:
    return await service.search_user_stats(guild_id, q, access_token)

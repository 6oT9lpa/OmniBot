from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.rbac import ActivityAuditPage, ActivityDashboardResponse
from activity.server.services.dashboard_service import ActivityDashboardService

router = APIRouter()
service = ActivityDashboardService()


@router.get("/api/activity/dashboard", response_model=ActivityDashboardResponse)
async def get_activity_dashboard(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivityDashboardResponse:
    return await service.get_dashboard(guild_id, access_token)


@router.get("/api/activity/audit", response_model=ActivityAuditPage)
async def list_activity_audit_events(
    guild_id: int = Query(gt=0),
    q: str = Query(default="", max_length=200),
    actor: str = Query(default="", max_length=100),
    date_from: str = Query(default="", max_length=32),
    date_to: str = Query(default="", max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivityAuditPage:
    return await service.list_audit_events(
        guild_id,
        access_token,
        query=q,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

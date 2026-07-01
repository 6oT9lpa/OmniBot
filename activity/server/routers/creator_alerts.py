from typing import Any

from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.creator_alerts import CreatorAlertSourcePayload, CreatorAlertTestPayload
from activity.server.services.creator_alert_service import CreatorAlertService

router = APIRouter()
service = CreatorAlertService()


@router.get("/api/creator-alerts/sources")
async def list_creator_alert_sources(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> list[dict[str, Any]]:
    return await service.list_sources(guild_id, access_token)


@router.put("/api/creator-alerts/sources")
async def save_creator_alert_source(
    payload: CreatorAlertSourcePayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.save_source(payload, access_token)


@router.delete("/api/creator-alerts/sources/{source_id}")
async def delete_creator_alert_source(
    source_id: int,
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.delete_source(guild_id, source_id, access_token)


@router.post("/api/creator-alerts/test")
async def preview_creator_alert(
    payload: CreatorAlertTestPayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.preview_alert(payload, access_token)

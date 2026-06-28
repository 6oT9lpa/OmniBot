from typing import Any

from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.welcome import WelcomeConfigPayload
from activity.server.services.welcome_service import ActivityWelcomeService

router = APIRouter()
service = ActivityWelcomeService()


@router.get("/api/welcome/config")
async def get_welcome_config(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.get_config(guild_id, access_token)


@router.put("/api/welcome/config")
async def save_welcome_config(
    payload: WelcomeConfigPayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.save_config(payload, access_token)


@router.delete("/api/welcome/config")
async def reset_welcome_config(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.reset_config(guild_id, access_token)


@router.post("/api/welcome/test")
async def send_welcome_test(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return await service.send_test_message(guild_id, access_token)

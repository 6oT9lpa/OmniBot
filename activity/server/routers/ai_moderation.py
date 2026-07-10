from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.ai_moderation_channels import AiModerationChannelsPayload
from activity.server.schemas.ai_moderation_policy import AiModerationPolicyPayload
from activity.server.services.ai_moderation_service import AiModerationService

router = APIRouter()
service = AiModerationService()


@router.get("/api/ai-moderator/settings")
async def get_ai_moderator_settings(guild_id: int = Query(gt=0), access_token: str = Depends(require_bearer_token)) -> dict[str, object]:
    return await service.get_settings(guild_id, access_token)


@router.put("/api/ai-moderator/channels")
async def save_ai_moderator_channels(payload: AiModerationChannelsPayload, access_token: str = Depends(require_bearer_token)) -> dict[str, object]:
    return await service.save_channels(payload, access_token)


@router.put("/api/ai-moderator/policy")
async def save_ai_moderator_policy(payload: AiModerationPolicyPayload, access_token: str = Depends(require_bearer_token)) -> dict[str, object]:
    return await service.save_policy(payload, access_token)

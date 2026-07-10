from core.domain.ai_moderation_guild_policy import AiModerationGuildPolicy
from pydantic import BaseModel, ConfigDict, Field


class AiModerationPolicyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guild_id: int = Field(gt=0)
    policy: AiModerationGuildPolicy

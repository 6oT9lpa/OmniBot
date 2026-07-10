from pydantic import BaseModel, ConfigDict, Field


class AiModerationPolicyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guild_id: int = Field(gt=0)
    policy: dict[str, object] = Field(max_length=32)

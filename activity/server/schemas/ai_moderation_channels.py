from pydantic import BaseModel, ConfigDict, Field


class AiModerationChannelsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guild_id: int = Field(gt=0)
    channel_ids: list[int] = Field(max_length=100)

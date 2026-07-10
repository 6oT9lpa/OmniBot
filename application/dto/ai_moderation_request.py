from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiModerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    guild_id: int = Field(gt=0)
    channel_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    message_id: int = Field(gt=0)
    raw_text: str = Field(max_length=8_000)
    created_at: datetime
    reply_to_message_id: int | None = Field(default=None, gt=0)
    mention_count: int = Field(default=0, ge=0, le=100)
    role_mention_count: int = Field(default=0, ge=0, le=100)
    channel_mention_count: int = Field(default=0, ge=0, le=100)
    has_attachments: bool = False
    attachment_count: int = Field(default=0, ge=0, le=50)
    recent_messages: tuple[str, ...] = Field(default=(), max_length=20)
    recent_message_timestamps: tuple[datetime, ...] = Field(default=(), max_length=20)

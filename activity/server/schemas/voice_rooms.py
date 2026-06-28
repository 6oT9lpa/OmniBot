from typing import Optional

from pydantic import BaseModel, Field


class VoiceRoomUpdatePayload(BaseModel):
    guild_id: int = Field(gt=0)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_limit: Optional[int] = Field(default=None, ge=0, le=99)
    locked: Optional[bool] = None
    owner_id: Optional[int] = Field(default=None, gt=0)
    persistent: Optional[bool] = None
    rtc_region: Optional[str] = Field(default=None, max_length=32)
    invite_user_id: Optional[int] = Field(default=None, gt=0)
    kick_user_id: Optional[int] = Field(default=None, gt=0)
    ban_user_id: Optional[int] = Field(default=None, gt=0)

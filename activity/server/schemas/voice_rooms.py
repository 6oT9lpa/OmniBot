from typing import Optional

from pydantic import BaseModel, Field, field_validator


class VoiceRoomUpdatePayload(BaseModel):
    guild_id: int = Field(gt=0)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_limit: Optional[int] = Field(default=None, ge=0, le=99)
    locked: Optional[bool] = None
    owner_id: Optional[int] = Field(default=None, gt=0)
    admin_id: Optional[int] = Field(default=None, gt=0)
    claim_admin: Optional[bool] = None
    release_admin: Optional[bool] = None
    persistent: Optional[bool] = None
    rtc_region: Optional[str] = Field(default=None, max_length=32)
    invite_user_id: Optional[int] = Field(default=None, gt=0)
    kick_user_id: Optional[int] = Field(default=None, gt=0)
    ban_user_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("rtc_region")
    @classmethod
    def validate_rtc_region(cls, value: Optional[str]) -> Optional[str]:
        if value == "europe":
            raise ValueError("Discord API does not support rtc_region=europe")
        return value

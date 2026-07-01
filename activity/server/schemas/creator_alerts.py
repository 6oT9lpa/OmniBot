from typing import Literal, Optional

from pydantic import BaseModel, Field


class CreatorAlertSourcePayload(BaseModel):
    guild_id: int = Field(gt=0)
    id: Optional[int] = Field(default=None, gt=0)
    platform: Literal["twitch", "youtube", "kick"]
    channel_url: str = Field(min_length=1, max_length=2048)
    channel_name: Optional[str] = Field(default=None, max_length=120)
    external_channel_id: Optional[str] = Field(default=None, max_length=160)
    alert_kind: Literal["stream", "video", "short"] = "stream"
    title_template: Optional[str] = Field(default=None, max_length=256)
    description_template: Optional[str] = Field(default=None, max_length=2000)
    template: Optional[str] = Field(default=None, max_length=2000)
    button_label: str = Field(default="Watch", min_length=1, max_length=80)
    color: int = Field(default=0x5865F2, ge=0, le=0xFFFFFF)
    ping_role_id: Optional[int] = Field(default=None, gt=0)
    active: bool = True
    user_id: Optional[int] = Field(default=None, gt=0)


class CreatorAlertTestPayload(BaseModel):
    guild_id: int = Field(gt=0)
    platform: Literal["twitch", "youtube", "kick"]
    alert_kind: Literal["stream", "video", "short"] = "stream"
    channel_name: str = Field(min_length=1, max_length=120)
    channel_url: str = Field(min_length=1, max_length=2048)
    title_template: Optional[str] = Field(default=None, max_length=256)
    description_template: Optional[str] = Field(default=None, max_length=2000)
    template: Optional[str] = Field(default=None, max_length=2000)
    button_label: str = Field(default="Watch", min_length=1, max_length=80)
    color: int = Field(default=0x5865F2, ge=0, le=0xFFFFFF)
    ping_role_id: Optional[int] = Field(default=None, gt=0)
    game: str = Field(default="Just Chatting", max_length=120)

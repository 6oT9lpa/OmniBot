import re
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from activity.server.schemas.validators import validate_public_https_url


_DIRECT_CHANNEL_REFERENCE = re.compile(r"^@?[A-Za-z0-9_-]{3,128}$")


def _validate_creator_channel_url(platform: str, value: str) -> str:
    candidate = value.strip()
    if _DIRECT_CHANNEL_REFERENCE.fullmatch(candidate):
        return candidate

    normalized = validate_public_https_url(candidate)
    host = (urlparse(normalized).hostname or "").lower()
    allowed_hosts = {
        "twitch": {"twitch.tv", "www.twitch.tv", "m.twitch.tv"},
        "youtube": {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"},
        "kick": {"kick.com", "www.kick.com"},
    }
    if host not in allowed_hosts[platform]:
        raise ValueError(f"The URL must point to {platform}")
    return normalized


class CreatorAlertSourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
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

    @model_validator(mode="after")
    def validate_channel_url(self) -> "CreatorAlertSourcePayload":
        self.channel_url = _validate_creator_channel_url(self.platform, self.channel_url)
        return self

    @field_validator("external_channel_id")
    @classmethod
    def validate_external_channel_id(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not _DIRECT_CHANNEL_REFERENCE.fullmatch(value.strip()):
            raise ValueError("Invalid external channel identifier")
        return value.strip() if value else None


class CreatorAlertTestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
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

    @model_validator(mode="after")
    def validate_channel_url(self) -> "CreatorAlertTestPayload":
        self.channel_url = _validate_creator_channel_url(self.platform, self.channel_url)
        return self

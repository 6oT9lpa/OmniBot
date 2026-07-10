from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from activity.server.schemas.validators import validate_public_https_url


class WelcomeConfigPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guild_id: int = Field(gt=0)
    title: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=4096)
    thumbnail_url: Optional[str] = Field(default=None, max_length=2048)
    footer_text: Optional[str] = Field(default=None, max_length=2048)
    footer_icon_url: Optional[str] = Field(default=None, max_length=2048)
    color: Optional[int] = Field(default=None, ge=0, le=0xFFFFFF)
    is_enabled: bool = True
    rules_channel_id: Optional[int] = Field(default=None, gt=0)
    roles_channel_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("thumbnail_url", "footer_icon_url")
    @classmethod
    def validate_image_url(cls, value: Optional[str]) -> Optional[str]:
        return validate_public_https_url(value) if value else None

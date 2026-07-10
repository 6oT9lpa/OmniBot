from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from activity.server.schemas.validators import validate_public_https_url


class DevBlogEmbedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, max_length=256)
    description: str = Field(min_length=1, max_length=4096)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    color: int = Field(default=0x5865F2, ge=0, le=0xFFFFFF)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: Optional[str]) -> Optional[str]:
        return validate_public_https_url(value) if value else None


class DevBlogPostPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guild_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    content: Optional[str] = Field(default=None, max_length=2000)
    embeds: list[DevBlogEmbedPayload] = Field(min_length=1, max_length=10)
    status: Literal["draft", "published"] = "published"
    image_render_mode: Literal["gallery_bottom", "inline_between_text"] = "gallery_bottom"

    @model_validator(mode="after")
    def validate_discord_components_v2_budget(self) -> "DevBlogPostPayload":
        total = len(self.title) + len(self.content or "")
        for embed in self.embeds:
            total += len(embed.title or "")
            total += len(embed.description)
        if total > 4000:
            raise ValueError("Discord Components V2 text display allows up to 4000 characters")
        return self

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VoiceRoomCreateSchema(BaseModel):
    """Валидация создания голосовой комнаты."""

    channel_id: int = Field(gt=0)
    guild_id: int = Field(gt=0)
    owner_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Room name must not be blank")
        return stripped


class VoiceRenameSchema(BaseModel):
    """Валидация переименования комнаты."""

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Name must not be blank")
        return stripped


class VoiceLimitSchema(BaseModel):
    """Валидация лимита пользователей."""

    limit: int = Field(ge=0, le=99)


class VoiceInviteSchema(BaseModel):
    """Валидация ID пользователя при приглашении."""

    user_id: int = Field(gt=0)
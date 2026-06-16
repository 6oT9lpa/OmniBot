from __future__ import annotations

import re
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict

from core.domain.value_objects import PunishmentType


class ReasonSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    value: str = Field(min_length=1, max_length=500)

    @field_validator("value")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason must not be empty")
        if "http://" in v.lower() or "https://" in v.lower() or "discord.gg/" in v.lower():
            raise ValueError("Links are not allowed in reason")
        if "`" in v or "*" in v or "_" in v or "~" in v or "||" in v:
            raise ValueError("Markdown injection is not allowed in reason")
        if len(v) > 500:
            raise ValueError("Reason must not exceed 500 characters")
        return v.strip()


class UserIdSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    user_id: int = Field(gt=0)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Invalid Discord user ID")
        return v


class DeleteMessageDaysSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    delete_message_days: int = Field(default=1, ge=1, le=7)

    @field_validator("delete_message_days")
    @classmethod
    def validate_delete_message_days(cls, v: int) -> int:
        if v < 1 or v > 7:
            raise ValueError("Delete message days must be between 1 and 7")
        return v


class DurationSchema(BaseModel):
    model_config = ConfigDict(strict=True)

    duration_seconds: Optional[int] = Field(default=None, gt=0)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Duration must be greater than 0")
        return v

class MuteCommandSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    user: Any
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    reason: str = Field(min_length=1, max_length=500, default="Violation of rules")

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Duration must be greater than 0")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason must not be empty")
        if "http://" in v.lower() or "https://" in v.lower() or "discord.gg/" in v.lower():
            raise ValueError("Links are not allowed in reason")
        if len(v) > 500:
            raise ValueError("Reason must not exceed 500 characters")
        return v.strip()

class BanCommandSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    user: Any
    reason: str = Field(min_length=1, max_length=500, default="Violation of rules")
    delete_message_days: int = Field(default=1, ge=1, le=7)
    duration_seconds: Optional[int] = Field(default=None, gt=0)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Duration must be greater than 0")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason must not be empty")
        if "http://" in v.lower() or "https://" in v.lower() or "discord.gg/" in v.lower():
            raise ValueError("Links are not allowed in reason")
        if len(v) > 500:
            raise ValueError("Reason must not exceed 500 characters")
        return v.strip()

    @field_validator("delete_message_days")
    @classmethod
    def validate_delete_message_days(cls, v: int) -> int:
        if v < 1 or v > 7:
            raise ValueError("Delete message days must be between 1 and 7")
        return v


class WarnCommandSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    user: Any
    reason: str = Field(min_length=1, max_length=500, default="Violation of rules")
    duration_seconds: Optional[int] = Field(default=None, gt=0)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason must not be empty")
        if "http://" in v.lower() or "https://" in v.lower() or "discord.gg/" in v.lower():
            raise ValueError("Links are not allowed in reason")
        if len(v) > 500:
            raise ValueError("Reason must not exceed 500 characters")
        return v.strip()


class KickCommandSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    user: Any
    reason: str = Field(min_length=1, max_length=500, default="Violation of rules")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason must not be empty")
        if "http://" in v.lower() or "https://" in v.lower() or "discord.gg/" in v.lower():
            raise ValueError("Links are not allowed in reason")
        if len(v) > 500:
            raise ValueError("Reason must not exceed 500 characters")
        return v.strip()
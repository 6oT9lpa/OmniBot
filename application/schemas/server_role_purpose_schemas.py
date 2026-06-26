from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from core.domain.server_role_purpose import ServerRolePurpose


class ServerRolePurposeSchema(BaseModel):
    guild_id: int = Field(gt=0)
    purpose: ServerRolePurpose
    role_id: int = Field(gt=0)

    @field_validator("purpose")
    @classmethod
    def validate_assignable_activity_purpose(
        cls,
        value: ServerRolePurpose,
    ) -> ServerRolePurpose:
        if value not in ServerRolePurpose:
            raise ValueError("Unknown activity role purpose")
        return value

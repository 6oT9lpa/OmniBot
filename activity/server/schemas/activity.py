from typing import Optional

from pydantic import BaseModel, Field

from core.domain.activity_user_type import ActivityUserType
from core.domain.channel_purpose import ChannelPurpose
from core.domain.server_role_purpose import ServerRolePurpose


class ActivityUser(BaseModel):
    id: str
    username: str
    discriminator: Optional[str] = None
    global_name: Optional[str] = None
    avatar: Optional[str] = None


class ActivityAccess(BaseModel):
    is_admin: bool
    is_streamer: bool
    is_developer: bool


class ActivitySession(BaseModel):
    user: ActivityUser
    guild_id: str
    user_type: ActivityUserType
    access: ActivityAccess
    is_admin: bool
    access_level: str
    activity_roles: list[str] = Field(default_factory=list)
    permissions: dict[str, str] = Field(default_factory=dict)
    available_modules: list[str] = Field(default_factory=list)


class ActivityRolePayload(BaseModel):
    guild_id: int = Field(gt=0)
    purpose: ServerRolePurpose
    role_id: int = Field(gt=0)


class ActivityHealthSignal(BaseModel):
    name: str
    value: str
    status: str
    latency_ms: Optional[int] = None


class ActivityHealthResponse(BaseModel):
    guild_id: str
    signals: list[ActivityHealthSignal]
    bot_latency_ms: Optional[int] = None


class ChannelPurposePayload(BaseModel):
    guild_id: int = Field(gt=0)
    purpose: ChannelPurpose
    channel_id: int = Field(gt=0)

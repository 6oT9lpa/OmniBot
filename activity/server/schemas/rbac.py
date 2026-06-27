from typing import Optional

from pydantic import BaseModel, Field


class AccessDeniedDetail(BaseModel):
    code: str
    message: str
    can_sync_roles: bool = False


class ActivityAccessRole(BaseModel):
    id: int
    guild_id: int
    slug: str
    name: str
    is_builtin: bool
    modules: dict[str, str] = Field(default_factory=dict)


class ActivityAccessRoleCreate(BaseModel):
    guild_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=48)


class ActivityAccessRoleModulesPayload(BaseModel):
    guild_id: int = Field(gt=0)
    modules: dict[str, str]


class ActivitySyncedRoleAssignmentPayload(BaseModel):
    guild_id: int = Field(gt=0)
    access_role_ids: list[int] = Field(default_factory=list)


class ActivitySyncedRole(BaseModel):
    role_id: str
    guild_id: int
    name: str
    color: int = 0
    position: int = 0
    permissions: int = 0
    is_admin: bool = False
    managed: bool = False
    mentionable: bool = False
    synced_at: Optional[str] = None
    access_roles: list[ActivityAccessRole] = Field(default_factory=list)


class ActivityRoleSyncResponse(BaseModel):
    guild_id: int
    synced_count: int
    admin_roles_count: int
    roles: list[ActivitySyncedRole]


class ActivityDashboardMetric(BaseModel):
    modules_ready: int
    modules_total: int
    ai_checks_today: int
    ai_flagged_today: int
    creator_sources: int
    bot_latency_ms: Optional[int] = None


class ActivityAuditEvent(BaseModel):
    id: int
    guild_id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    event_type: str
    details: Optional[str] = None
    created_at: str


class ActivityAuditPage(BaseModel):
    items: list[ActivityAuditEvent]
    total: int
    limit: int
    offset: int


class ActivityDashboardResponse(BaseModel):
    metrics: ActivityDashboardMetric
    audit: list[ActivityAuditEvent]

from fastapi import APIRouter, Depends, Path, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.rbac import (
    ActivityAccessRole,
    ActivityAccessRoleCreate,
    ActivityAccessRoleModulesPayload,
    ActivityRoleSyncResponse,
    ActivitySyncedRole,
    ActivitySyncedRoleAssignmentPayload,
)
from activity.server.services.rbac_service import ActivityRbacService

router = APIRouter()
service = ActivityRbacService()


@router.post("/api/activity/rbac/roles/sync", response_model=ActivityRoleSyncResponse)
async def sync_activity_roles(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivityRoleSyncResponse:
    return await service.sync_roles(guild_id, access_token)


@router.get("/api/activity/rbac/access-roles", response_model=list[ActivityAccessRole])
async def list_activity_access_roles(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> list[ActivityAccessRole]:
    return await service.list_access_roles(guild_id, access_token)


@router.post("/api/activity/rbac/access-roles", response_model=ActivityAccessRole)
async def create_activity_access_role(
    payload: ActivityAccessRoleCreate,
    access_token: str = Depends(require_bearer_token),
) -> ActivityAccessRole:
    return await service.create_access_role(payload.guild_id, payload.name, access_token)


@router.put("/api/activity/rbac/access-roles/{role_id}/modules", response_model=ActivityAccessRole)
async def update_activity_access_role_modules(
    payload: ActivityAccessRoleModulesPayload,
    role_id: int = Path(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivityAccessRole:
    return await service.update_access_role_modules(payload.guild_id, role_id, payload.modules, access_token)


@router.get("/api/activity/rbac/synced-roles", response_model=list[ActivitySyncedRole])
async def list_activity_synced_roles(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> list[ActivitySyncedRole]:
    return await service.list_synced_roles(guild_id, access_token)


@router.put("/api/activity/rbac/synced-roles/{discord_role_id}/assignments", response_model=ActivitySyncedRole)
async def update_activity_synced_role_assignments(
    payload: ActivitySyncedRoleAssignmentPayload,
    discord_role_id: int = Path(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> ActivitySyncedRole:
    return await service.update_synced_role_assignments(
        payload.guild_id,
        discord_role_id,
        payload.access_role_ids,
        access_token,
    )

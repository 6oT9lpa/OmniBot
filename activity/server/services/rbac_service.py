from typing import Any

from fastapi import HTTPException

from activity.server.config import activity_server_config
from activity.server.dependencies import get_db
from activity.server.schemas.rbac import (
    ActivityAccessRole,
    ActivityRoleSyncResponse,
    ActivitySyncedRole,
)
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.audit_service import ActivityAuditService
from activity.server.services.discord_service import DiscordService
from activity.server.utils.rbac import (
    ACCESS_ROLE_CONFIGURABLE_MODULES,
    MODULE_ORDER,
    normalize_access_role_slug,
    normalize_module_permissions,
    normalize_permission,
)
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityRbacService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._audit_service = ActivityAuditService()
        self._discord = DiscordService()

    async def sync_roles(self, guild_id: int, access_token: str) -> ActivityRoleSyncResponse:
        actor = await self._access_service.ensure_discord_administrator(access_token, str(guild_id))
        logger.info("Starting Activity role sync guild_id=%s actor_id=%s", guild_id, actor.get("id"))
        roles = await self._discord.list_roles(str(guild_id))
        admin_role = await self._get_access_role_by_slug(guild_id, "administrator")

        seen_role_ids: list[int] = []
        admin_roles_count = 0
        for role in roles:
            role_id = int(role.id)
            is_admin = bool(role.permissions & activity_server_config.administrator_permission)
            seen_role_ids.append(role_id)
            if is_admin:
                admin_roles_count += 1

            await get_db().execute(
                """
                INSERT INTO activity_synced_roles (
                    guild_id,
                    role_id,
                    name,
                    color,
                    position,
                    permissions,
                    is_admin,
                    managed,
                    mentionable,
                    synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(guild_id, role_id)
                DO UPDATE SET
                    name = excluded.name,
                    color = excluded.color,
                    position = excluded.position,
                    permissions = excluded.permissions,
                    is_admin = excluded.is_admin,
                    managed = excluded.managed,
                    mentionable = excluded.mentionable,
                    synced_at = excluded.synced_at
                """,
                (
                    guild_id,
                    role_id,
                    role.name,
                    role.color,
                    role.position,
                    role.permissions,
                    is_admin,
                    role.managed,
                    role.mentionable,
                ),
            )

            if is_admin and admin_role:
                await get_db().execute(
                    """
                    INSERT INTO activity_synced_role_assignments (guild_id, discord_role_id, access_role_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, discord_role_id, access_role_id) DO NOTHING
                    """,
                    (guild_id, role_id, admin_role.id),
                )

        if seen_role_ids:
            placeholders = ",".join("?" for _ in seen_role_ids)
            await get_db().execute(
                f"""
                DELETE FROM activity_synced_roles
                WHERE guild_id = ?
                  AND role_id NOT IN ({placeholders})
                """,
                (guild_id, *seen_role_ids),
            )

        await get_db().commit()
        logger.info(
            "Activity role sync completed guild_id=%s synced=%s admin_roles=%s",
            guild_id,
            len(roles),
            admin_roles_count,
        )
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(actor["id"]),
            actor_name=self._display_name(actor),
            event_type="activity_roles_synced",
            details=f"Synchronized {len(roles)} Discord roles. Administrator roles: {admin_roles_count}.",
        )

        synced_roles = await self.list_synced_roles(guild_id, access_token)
        return ActivityRoleSyncResponse(
            guild_id=guild_id,
            synced_count=len(roles),
            admin_roles_count=admin_roles_count,
            roles=synced_roles,
        )

    async def list_access_roles(self, guild_id: int, access_token: str) -> list[ActivityAccessRole]:
        await self._access_service.ensure_admin(access_token, str(guild_id))
        await self._access_service.ensure_builtin_access_roles(guild_id)
        logger.info("Listing Activity access roles guild_id=%s", guild_id)
        return await self._list_access_roles_unchecked(guild_id)

    async def get_access_control(self, guild_id: int, access_token: str) -> dict[str, Any]:
        await self._access_service.ensure_admin(access_token, str(guild_id))
        await self._access_service.ensure_builtin_access_roles(guild_id)
        logger.info("Loading aggregated Access Control data guild_id=%s", guild_id)
        return {"access_roles": await self._list_access_roles_unchecked(guild_id)}

    async def get_role_panels(self, guild_id: int, access_token: str) -> dict[str, Any]:
        await self._access_service.ensure_admin(access_token, str(guild_id))
        await self._access_service.ensure_builtin_access_roles(guild_id)
        logger.info("Loading aggregated Role Panels data guild_id=%s", guild_id)
        return {
            "access_roles": await self._list_access_roles_unchecked(guild_id),
            "synced_roles": await self._list_synced_roles_unchecked(guild_id),
        }

    async def _list_access_roles_unchecked(self, guild_id: int) -> list[ActivityAccessRole]:
        rows = await get_db().fetch_all(
            """
            SELECT * FROM activity_access_roles
            WHERE guild_id = ?
            ORDER BY is_builtin DESC, id ASC
            """,
            (guild_id,),
        )
        return [await self._to_access_role(row) for row in rows]

    async def create_access_role(self, guild_id: int, name: str, access_token: str) -> ActivityAccessRole:
        actor = await self._access_service.ensure_admin(access_token, str(guild_id))
        clean_name = name.strip()
        logger.info("Creating custom Activity access role guild_id=%s actor_id=%s name=%s", guild_id, actor.get("id"), clean_name)
        if await self._name_exists(guild_id, clean_name):
            raise HTTPException(status_code=409, detail="Activity role name already exists")

        slug = await self._unique_slug(guild_id, normalize_access_role_slug(clean_name))
        cursor = await get_db().execute(
            """
            INSERT INTO activity_access_roles (guild_id, slug, name, is_builtin)
            VALUES (?, ?, ?, 0)
            """,
            (guild_id, slug, clean_name),
        )
        await get_db().commit()
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(actor["id"]),
            actor_name=self._display_name(actor),
            target_id=cursor.lastrowid,
            target_name=clean_name,
            event_type="activity_access_role_created",
            details=f"Created Activity role {clean_name}.",
        )
        row = await get_db().fetch_one("SELECT * FROM activity_access_roles WHERE id = ?", (cursor.lastrowid,))
        return await self._to_access_role(row)

    async def delete_access_role(self, guild_id: int, role_id: int, access_token: str) -> dict[str, Any]:
        actor = await self._access_service.ensure_admin(access_token, str(guild_id))
        row = await self._get_access_role(guild_id, role_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Activity role not found")
        if row["is_builtin"]:
            logger.warning("Blocked built-in Activity role deletion guild_id=%s role_id=%s", guild_id, role_id)
            raise HTTPException(status_code=400, detail="Built-in Activity roles cannot be deleted")

        await get_db().execute("DELETE FROM activity_access_roles WHERE guild_id = ? AND id = ?", (guild_id, role_id))
        await get_db().commit()
        logger.info("Deleted custom Activity access role guild_id=%s role_id=%s actor_id=%s", guild_id, role_id, actor.get("id"))
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(actor["id"]),
            actor_name=self._display_name(actor),
            target_id=role_id,
            target_name=row["name"],
            event_type="activity_access_role_deleted",
            details=f"Deleted Activity role {row['name']}.",
        )
        return {"role_id": role_id, "deleted": True}

    async def update_access_role_modules(
        self,
        guild_id: int,
        role_id: int,
        modules: dict[str, str],
        access_token: str,
    ) -> ActivityAccessRole:
        actor = await self._access_service.ensure_admin(access_token, str(guild_id))
        row = await self._get_access_role(guild_id, role_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Activity role not found")
        if row["slug"] == "administrator":
            logger.warning("Blocked administrator Activity role update guild_id=%s role_id=%s", guild_id, role_id)
            raise HTTPException(status_code=400, detail="Administrator Activity role permissions are immutable")

        normalized = normalize_module_permissions(modules)
        for module_key, permission in normalized.items():
            await get_db().execute(
                """
                INSERT INTO activity_access_role_modules (access_role_id, module_key, permission)
                VALUES (?, ?, ?)
                ON CONFLICT(access_role_id, module_key)
                DO UPDATE SET permission = excluded.permission
                """,
                (role_id, module_key, normalize_permission(permission)),
            )
        await get_db().execute(
            "UPDATE activity_access_roles SET updated_at = datetime('now', 'localtime') WHERE id = ?",
            (role_id,),
        )
        await get_db().commit()
        logger.info(
            "Updated Activity role modules guild_id=%s role_id=%s modules=%s",
            guild_id,
            role_id,
            ",".join(ACCESS_ROLE_CONFIGURABLE_MODULES),
        )
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(actor["id"]),
            actor_name=self._display_name(actor),
            target_id=role_id,
            target_name=row["name"],
            event_type="activity_access_role_modules_updated",
            details=f"Updated module permissions for {row['name']}.",
        )
        return await self._to_access_role(await self._get_access_role(guild_id, role_id))

    async def list_synced_roles(self, guild_id: int, access_token: str) -> list[ActivitySyncedRole]:
        await self._access_service.ensure_admin(access_token, str(guild_id))
        logger.info("Listing synced Discord roles guild_id=%s", guild_id)
        return await self._list_synced_roles_unchecked(guild_id)

    async def _list_synced_roles_unchecked(self, guild_id: int) -> list[ActivitySyncedRole]:
        rows = await get_db().fetch_all(
            """
            SELECT * FROM activity_synced_roles
            WHERE guild_id = ?
            ORDER BY position DESC, name ASC
            """,
            (guild_id,),
        )
        return [await self._to_synced_role(row) for row in rows]

    async def update_synced_role_assignments(
        self,
        guild_id: int,
        discord_role_id: int,
        access_role_ids: list[int],
        access_token: str,
    ) -> ActivitySyncedRole:
        actor = await self._access_service.ensure_admin(access_token, str(guild_id))
        logger.info(
            "Updating synced role assignments guild_id=%s discord_role_id=%s actor_id=%s access_role_ids=%s",
            guild_id,
            discord_role_id,
            actor.get("id"),
            access_role_ids,
        )
        synced_role = await get_db().fetch_one(
            "SELECT * FROM activity_synced_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, discord_role_id),
        )
        if synced_role is None:
            raise HTTPException(status_code=404, detail="Synced Discord role not found")

        unique_ids = sorted({int(role_id) for role_id in access_role_ids})
        if unique_ids:
            placeholders = ",".join("?" for _ in unique_ids)
            rows = await get_db().fetch_all(
                f"""
                SELECT id FROM activity_access_roles
                WHERE guild_id = ?
                  AND id IN ({placeholders})
                """,
                (guild_id, *unique_ids),
            )
            found_ids = {row["id"] for row in rows}
            missing_ids = [role_id for role_id in unique_ids if role_id not in found_ids]
            if missing_ids:
                raise HTTPException(status_code=400, detail=f"Unknown Activity roles: {missing_ids}")

        await get_db().execute(
            "DELETE FROM activity_synced_role_assignments WHERE guild_id = ? AND discord_role_id = ?",
            (guild_id, discord_role_id),
        )
        for access_role_id in unique_ids:
            await get_db().execute(
                """
                INSERT INTO activity_synced_role_assignments (guild_id, discord_role_id, access_role_id)
                VALUES (?, ?, ?)
                """,
                (guild_id, discord_role_id, access_role_id),
            )
        await get_db().commit()
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(actor["id"]),
            actor_name=self._display_name(actor),
            target_id=discord_role_id,
            target_name=synced_role["name"],
            event_type="activity_synced_role_assignments_updated",
            details=f"Updated Activity role assignments for Discord role {synced_role['name']}.",
        )
        return await self._to_synced_role(synced_role)

    async def _to_access_role(self, row: dict[str, Any]) -> ActivityAccessRole:
        module_rows = await get_db().fetch_all(
            "SELECT module_key, permission FROM activity_access_role_modules WHERE access_role_id = ?",
            (row["id"],),
        )
        modules = {key: "disabled" for key in MODULE_ORDER}
        modules.update({item["module_key"]: item["permission"] for item in module_rows})
        return ActivityAccessRole(
            id=row["id"],
            guild_id=row["guild_id"],
            slug=row["slug"],
            name=row["name"],
            is_builtin=bool(row["is_builtin"]),
            modules=modules,
        )

    async def _to_synced_role(self, row: dict[str, Any]) -> ActivitySyncedRole:
        access_roles = await self._get_assignments(row["guild_id"], row["role_id"])
        return ActivitySyncedRole(
            role_id=str(row["role_id"]),
            guild_id=row["guild_id"],
            name=row["name"],
            color=row["color"],
            position=row["position"],
            permissions=row["permissions"],
            is_admin=bool(row["is_admin"]),
            managed=bool(row["managed"]),
            mentionable=bool(row["mentionable"]),
            synced_at=row["synced_at"],
            access_roles=access_roles,
        )

    async def _get_assignments(self, guild_id: int, discord_role_id: int) -> list[ActivityAccessRole]:
        rows = await get_db().fetch_all(
            """
            SELECT ar.*
            FROM activity_access_roles ar
            JOIN activity_synced_role_assignments assignment
              ON assignment.access_role_id = ar.id
            WHERE assignment.guild_id = ?
              AND assignment.discord_role_id = ?
            ORDER BY ar.is_builtin DESC, ar.id ASC
            """,
            (guild_id, discord_role_id),
        )
        return [await self._to_access_role(row) for row in rows]

    async def _get_access_role(self, guild_id: int, role_id: int) -> dict[str, Any] | None:
        return await get_db().fetch_one(
            "SELECT * FROM activity_access_roles WHERE guild_id = ? AND id = ?",
            (guild_id, role_id),
        )

    async def _get_access_role_by_slug(self, guild_id: int, slug: str) -> ActivityAccessRole | None:
        row = await get_db().fetch_one(
            "SELECT * FROM activity_access_roles WHERE guild_id = ? AND slug = ?",
            (guild_id, slug),
        )
        return await self._to_access_role(row) if row else None

    async def _name_exists(self, guild_id: int, name: str) -> bool:
        row = await get_db().fetch_one(
            "SELECT 1 FROM activity_access_roles WHERE guild_id = ? AND lower(name) = lower(?)",
            (guild_id, name),
        )
        return row is not None

    async def _unique_slug(self, guild_id: int, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while await self._get_access_role_by_slug(guild_id, slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    def _display_name(self, user: dict[str, Any]) -> str:
        return user.get("global_name") or user.get("username") or str(user.get("id"))

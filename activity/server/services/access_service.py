import asyncio
import hashlib
import time
from typing import Any

from fastapi import HTTPException

from activity.server.config import activity_server_config
from activity.server.dependencies import get_db
from activity.server.services.discord_service import DiscordService
from activity.server.utils.http_client import discord_async_client
from activity.server.utils.rbac import BUILTIN_ACCESS_ROLES, MODULE_ORDER, merge_module_permissions
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityAccessService:
    _context_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
    _context_inflight: dict[tuple[str, str], asyncio.Task[dict[str, Any]]] = {}
    _context_ttl_seconds = 20.0

    def __init__(self) -> None:
        self._discord = DiscordService()

    async def fetch_user_context(self, access_token: str, guild_id: str) -> dict[str, Any]:
        cache_key = (self._token_cache_key(access_token), guild_id)
        now = time.monotonic()
        cached = self._context_cache.get(cache_key)
        if cached and cached[0] > now:
            logger.debug("Using cached Discord user context guild_id=%s", guild_id)
            return self._clone_context(cached[1])

        inflight = self._context_inflight.get(cache_key)
        if inflight:
            logger.debug("Waiting for in-flight Discord user context guild_id=%s", guild_id)
            return self._clone_context(await inflight)

        task = asyncio.create_task(self._fetch_user_context_uncached(access_token, guild_id))
        self._context_inflight[cache_key] = task
        try:
            context = await task
            self._context_cache[cache_key] = (time.monotonic() + self._context_ttl_seconds, context)
            return self._clone_context(context)
        finally:
            self._context_inflight.pop(cache_key, None)

    async def _fetch_user_context_uncached(self, access_token: str, guild_id: str) -> dict[str, Any]:
        logger.info("Fetching Discord user context guild_id=%s", guild_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        async with discord_async_client(timeout=10) as client:
            user_response = await client.get(f"{activity_server_config.discord_api_base}/users/@me", headers=headers)
            guilds_response = await client.get(f"{activity_server_config.discord_api_base}/users/@me/guilds", headers=headers)

        if user_response.status_code >= 400:
            logger.warning("Discord user lookup failed guild_id=%s status=%s", guild_id, user_response.status_code)
            raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
        if guilds_response.status_code >= 400:
            logger.warning("Discord guild lookup failed guild_id=%s status=%s", guild_id, guilds_response.status_code)
            raise HTTPException(status_code=guilds_response.status_code, detail=guilds_response.text)

        user = user_response.json()
        current_guild = next((guild for guild in guilds_response.json() if guild.get("id") == guild_id), None)
        if current_guild is None:
            logger.warning("User id=%s is not a member of guild_id=%s", user.get("id"), guild_id)
            raise HTTPException(status_code=403, detail="User is not a member of this guild")

        permissions = int(current_guild.get("permissions") or 0)
        return {
            "user": user,
            "guild": current_guild,
            "permissions": permissions,
            "has_discord_admin": self._has_administrator_permission(permissions),
            "member_role_ids": await self._discord.fetch_member_role_ids(guild_id, user["id"]),
        }

    def _token_cache_key(self, access_token: str) -> str:
        return hashlib.sha256(access_token.encode("utf-8")).hexdigest()

    def _clone_context(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            **context,
            "member_role_ids": set(context.get("member_role_ids", set())),
        }

    async def fetch_user_and_access_state(self, access_token: str, guild_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        context = await self.fetch_user_context(access_token, guild_id)
        await self._ensure_builtin_access_roles(int(guild_id))

        if not await self._has_synced_roles(int(guild_id)):
            logger.warning(
                "Activity access denied because roles are not synced guild_id=%s user_id=%s can_sync=%s",
                guild_id,
                context["user"].get("id"),
                bool(context["has_discord_admin"]),
            )
            raise self._access_denied(
                "roles_not_synced",
                "Discord roles are not synchronized yet. Run /sync_role or press Sync roles if you are a server administrator.",
                bool(context["has_discord_admin"]),
            )

        access = await self._resolve_access_state(
            int(guild_id),
            context["member_role_ids"],
        )
        if not access["available_modules"]:
            logger.warning(
                "Activity access denied because no modules are configured guild_id=%s user_id=%s roles=%s",
                guild_id,
                context["user"].get("id"),
                sorted(context["member_role_ids"]),
            )
            raise self._access_denied(
                "access_not_configured",
                "Activity access levels are not configured for your Discord roles. Ask an administrator to configure Access Control.",
                False,
            )

        logger.info(
            "Activity access granted guild_id=%s user_id=%s level=%s modules=%s",
            guild_id,
            context["user"].get("id"),
            access["access_level"],
            ",".join(access["available_modules"]),
        )
        return context["user"], access

    async def ensure_admin(self, access_token: str, guild_id: str) -> dict[str, Any]:
        user, access = await self.fetch_user_and_access_state(access_token, guild_id)
        if not access["is_admin"]:
            logger.warning("Activity administrator access denied guild_id=%s user_id=%s", guild_id, user.get("id"))
            raise HTTPException(status_code=403, detail="Activity administrator permission is required")
        return user

    async def ensure_discord_administrator(self, access_token: str, guild_id: str) -> dict[str, Any]:
        # Discord administrators may bootstrap / sync roles, but panel access still comes from Activity roles.
        context = await self.fetch_user_context(access_token, guild_id)
        await self._ensure_builtin_access_roles(int(guild_id))
        if not context["has_discord_admin"]:
            logger.warning(
                "Discord administrator access denied guild_id=%s user_id=%s",
                guild_id,
                context["user"].get("id"),
            )
            raise HTTPException(status_code=403, detail="Discord administrator permission is required")
        logger.info("Discord administrator access granted guild_id=%s user_id=%s", guild_id, context["user"].get("id"))
        return context["user"]

    async def ensure_panel_access(self, access_token: str, guild_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        return await self.fetch_user_and_access_state(access_token, guild_id)

    async def ensure_module_access(
        self,
        access_token: str,
        guild_id: str,
        module_key: str,
        minimum_permission: str = "view",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user, access = await self.fetch_user_and_access_state(access_token, guild_id)
        actual_permission = access["permissions"].get(module_key, "disabled")
        if not self._permission_allows(actual_permission, minimum_permission):
            logger.warning(
                "Module access denied guild_id=%s user_id=%s module=%s actual=%s required=%s",
                guild_id,
                user.get("id"),
                module_key,
                actual_permission,
                minimum_permission,
            )
            raise HTTPException(status_code=403, detail=f"Module '{module_key}' access is required")
        logger.info(
            "Module access granted guild_id=%s user_id=%s module=%s permission=%s",
            guild_id,
            user.get("id"),
            module_key,
            actual_permission,
        )
        return user, access

    async def ensure_developer_or_admin(self, access_token: str, guild_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        user, access = await self.ensure_module_access(access_token, guild_id, "dev-blog", "publish")
        if not (access["is_admin"] or access["is_developer"] or self._permission_allows(access["permissions"].get("dev-blog", "disabled"), "publish")):
            raise HTTPException(status_code=403, detail="Developer or administrator access is required")
        return user, access

    async def ensure_builtin_access_roles(self, guild_id: int) -> None:
        await self._ensure_builtin_access_roles(guild_id)

    async def _resolve_access_state(
        self,
        guild_id: int,
        member_role_ids: set[int],
    ) -> dict[str, Any]:
        if await self._has_synced_admin_role(guild_id, member_role_ids):
            return self._build_access_state(["Administrator"], {key: "manage" for key in MODULE_ORDER}, "administrator")

        assigned_roles = await self._get_member_access_roles(guild_id, member_role_ids)
        if not assigned_roles:
            user_role = await self._get_access_role_by_slug(guild_id, "user")
            if user_role:
                assigned_roles = [user_role]
            else:
                return self._build_access_state([], {}, "ordinary")

        modules = merge_module_permissions([role["modules"] for role in assigned_roles])
        level = self._highest_access_level([role["slug"] for role in assigned_roles])
        role_names = [role["name"] for role in assigned_roles]
        return self._build_access_state(role_names, modules, level)

    async def _ensure_builtin_access_roles(self, guild_id: int) -> None:
        for definition in BUILTIN_ACCESS_ROLES:
            row = await self._get_access_role_by_slug(guild_id, str(definition["slug"]))
            if not row:
                logger.info("Creating built-in Activity role guild_id=%s slug=%s", guild_id, definition["slug"])
                cursor = await get_db().execute(
                    """
                    INSERT INTO activity_access_roles (guild_id, slug, name, is_builtin)
                    VALUES (?, ?, ?, 1)
                    """,
                    (guild_id, definition["slug"], definition["name"]),
                )
                await get_db().commit()
                role_id = cursor.lastrowid
            else:
                role_id = row["id"]

            for module_key, permission in dict(definition["modules"]).items():
                await get_db().execute(
                    """
                    INSERT INTO activity_access_role_modules (access_role_id, module_key, permission)
                    VALUES (?, ?, ?)
                    ON CONFLICT(access_role_id, module_key)
                    DO UPDATE SET permission = excluded.permission
                    """,
                    (role_id, module_key, permission),
                )
        await get_db().commit()

    async def _has_synced_roles(self, guild_id: int) -> bool:
        row = await get_db().fetch_one("SELECT 1 FROM activity_synced_roles WHERE guild_id = ? LIMIT 1", (guild_id,))
        return row is not None

    async def _has_synced_admin_role(self, guild_id: int, member_role_ids: set[int]) -> bool:
        if not member_role_ids:
            return False
        placeholders = ",".join("?" for _ in member_role_ids)
        row = await get_db().fetch_one(
            f"""
            SELECT 1
            FROM activity_synced_role_assignments assignment
            JOIN activity_access_roles access_role
              ON access_role.id = assignment.access_role_id
            WHERE assignment.guild_id = ?
              AND assignment.discord_role_id IN ({placeholders})
              AND access_role.slug = 'administrator'
            LIMIT 1
            """,
            (guild_id, *member_role_ids),
        )
        return row is not None

    async def _get_member_access_roles(self, guild_id: int, member_role_ids: set[int]) -> list[dict[str, Any]]:
        if not member_role_ids:
            return []
        placeholders = ",".join("?" for _ in member_role_ids)
        rows = await get_db().fetch_all(
            f"""
            SELECT DISTINCT ar.*
            FROM activity_access_roles ar
            JOIN activity_synced_role_assignments assignment
              ON assignment.access_role_id = ar.id
            WHERE assignment.guild_id = ?
              AND assignment.discord_role_id IN ({placeholders})
            ORDER BY ar.is_builtin DESC, ar.id ASC
            """,
            (guild_id, *member_role_ids),
        )
        return [await self._hydrate_access_role(row) for row in rows]

    async def _get_access_role_by_slug(self, guild_id: int, slug: str) -> dict[str, Any] | None:
        row = await get_db().fetch_one(
            "SELECT * FROM activity_access_roles WHERE guild_id = ? AND slug = ?",
            (guild_id, slug),
        )
        return await self._hydrate_access_role(row) if row else None

    async def _hydrate_access_role(self, row: dict[str, Any]) -> dict[str, Any]:
        modules = await get_db().fetch_all(
            "SELECT module_key, permission FROM activity_access_role_modules WHERE access_role_id = ?",
            (row["id"],),
        )
        return {
            **row,
            "is_builtin": bool(row.get("is_builtin")),
            "modules": {item["module_key"]: item["permission"] for item in modules},
        }

    def _build_access_state(self, role_names: list[str], modules: dict[str, str], level: str) -> dict[str, Any]:
        available_modules = [module for module in MODULE_ORDER if modules.get(module, "disabled") != "disabled"]
        return {
            "is_admin": level == "administrator",
            "is_streamer": level == "creator",
            "is_developer": level == "developer",
            "access_level": level,
            "activity_roles": role_names,
            "permissions": {module: modules.get(module, "disabled") for module in MODULE_ORDER},
            "available_modules": available_modules,
        }

    def _highest_access_level(self, slugs: list[str]) -> str:
        priority = ["administrator", "moderator", "developer", "creator", "user"]
        for slug in priority:
            if slug in slugs:
                return "ordinary" if slug == "user" else slug
        return "ordinary"

    def _has_administrator_permission(self, permissions: int) -> bool:
        return bool(permissions & activity_server_config.administrator_permission)

    def _permission_allows(self, actual: str, required: str) -> bool:
        from activity.server.utils.rbac import PERMISSION_ORDER, normalize_permission

        return PERMISSION_ORDER.index(normalize_permission(actual)) >= PERMISSION_ORDER.index(normalize_permission(required))

    def _access_denied(self, code: str, message: str, can_sync_roles: bool) -> HTTPException:
        return HTTPException(
            status_code=403,
            detail={"code": code, "message": message, "can_sync_roles": can_sync_roles},
        )

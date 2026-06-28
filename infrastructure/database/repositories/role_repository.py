from typing import List, Optional, Dict, Any
from datetime import datetime

from core.domain.activity_access import BUILTIN_ACCESS_ROLES, DISCORD_ADMINISTRATOR_PERMISSION
from core.interfaces.repositories import RoleRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RoleRepository(RoleRepositoryInterface, BaseRepository):
    _TABLE_NAME = "roles"
    _ALLOWED_COLUMNS = {
        "role_id", "guild_id", "name", "color", "position",
        "is_auto_assign", "is_public", "display_emoji",
        "created_at", "updated_at"
    }

    def __init__(self, db_manager: DatabaseManager, guild_id: int):
        super().__init__(db_manager)
        self._guild_id = guild_id

    async def add_role(
        self, 
        role_id: int,
        name: str,
        color: int = None,
        position: int = None,
        is_auto_assign: bool = False,
        is_public: bool = True,
        display_emoji: Optional[str] = None,
    ) -> bool:
        """Добавление или обновление ролей"""
        existing = await self.get_role(role_id)
        
        if existing:
            needs_update = False
            update_data = {}
            
            if existing["name"] != name:
                update_data["name"] = name
                needs_update = True
            if existing["color"] != color:
                update_data["color"] = color
                needs_update = True
            if existing["position"] != position:
                update_data["position"] = position
                needs_update = True
            if existing["display_emoji"] != display_emoji:
                update_data["display_emoji"] = display_emoji
                needs_update = True
            
            if needs_update:
                update_data["updated_at"] = "CURRENT_TIMESTAMP"
                for key, value in update_data.items():
                    await self.update(
                        data={key: value},
                        where_column="role_id",
                        where_value=role_id
                    )
                logger.debug(f"Updated role {name} ({role_id})")
            else:
                logger.debug(f"Role {name} ({role_id}) unchanged, skipping update")

        else:
            data = {
                "role_id": role_id,
                "guild_id": self._guild_id,
                "name": name,
                "color": color,
                "position": position,
                "is_auto_assign": 1 if is_auto_assign else 0,
                "is_public": 1 if is_public else 0,
                "display_emoji": display_emoji,
            }
            await self.insert(data)
            logger.info(f"Added new role: {name} ({role_id})")
        
        return True
        
    async def get_auto_assign_roles(self) -> List[int]:
        """Получить ID ролей для автовыдачи"""
        query = """
            SELECT role_id FROM roles 
            WHERE guild_id = ? AND is_auto_assign = 1
        """
        rows = await self.fetch_all(query, (self._guild_id,))
        logger.debug(f"Auto-assign roles for guild {self._guild_id}: {[row['role_id'] for row in rows]}")
        return [row["role_id"] for row in rows]
    
    async def set_auto_assign(self, role_id: int, is_auto_assign: bool) -> None:
        """Установить флаг автовыдачи"""
        await self.update(
            data={"is_auto_assign": 1 if is_auto_assign else 0},
            where_column="role_id",
            where_value=role_id
        )
        logger.info(f"Auto assign for role {role_id} set to {is_auto_assign}")
    
    async def set_public(self, role_id: int, is_public: bool) -> None:
        """Скрыть/показать роль в панели"""
        await self.update(
            data={"is_public": 1 if is_public else 0},
            where_column="role_id",
            where_value=role_id
        )
        logger.info(f"Public visibility for role {role_id} set to {is_public}")
    
    async def get_all_roles(self) -> List[Dict[str, Any]]:
        """Получить все роли сервера"""
        query = """
            SELECT role_id, name, color, position, 
                   is_auto_assign, is_public, display_emoji
            FROM roles 
            WHERE guild_id = ?
            ORDER BY position ASC
        """
        logger.debug(f"Fetching all roles for guild {self._guild_id}")
        return await self.fetch_all(query, (self._guild_id,))
    
    async def get_public_roles(self) -> List[Dict[str, Any]]:
        """Получить публичные роли (для панели)"""
        query = """
            SELECT role_id, name, color, display_emoji
            FROM roles 
            WHERE guild_id = ? AND is_public = 1
            ORDER BY position ASC
        """
        logger.debug(f"Fetching public roles for guild {self._guild_id}")
        return await self.fetch_all(query, (self._guild_id,))
    
    async def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        """Получить роль по ID"""
        logger.debug(f"Fetching role {role_id} for guild {self._guild_id}")
        return await self.get_by_id(role_id, id_column="role_id")
    
    async def sync_from_discord(self, discord_roles: List[Dict[str, Any]]) -> int:
        """Синхронизировать роли из Discord (для админки)"""
        synced_count = 0
        for role in discord_roles:
            await self.add_role(
                role_id=role["id"],
                name=role["name"],
                color=role.get("color"),
                position=role.get("position"),
                is_auto_assign=False,
                is_public=True,
                display_emoji=None
            )
            synced_count += 1
        
        logger.info(f"Synced {len(discord_roles)} roles from Discord")
        return synced_count
    
    async def sync_activity_roles_from_discord(self, guild_id: int, discord_roles: List[Dict[str, Any]]) -> int:
        # /sync_roles must populate Activity RBAC too; otherwise the Activity keeps returning roles_not_synced.
        logger.info("Syncing Activity RBAC Discord roles for guild_id=%s count=%s", guild_id, len(discord_roles))
        administrator_role_id = await self._ensure_activity_builtin_roles(guild_id)
        seen_role_ids: list[int] = []

        for role in discord_roles:
            role_id = int(role["id"])
            permissions = int(role.get("permissions") or 0)
            is_admin = bool(permissions & DISCORD_ADMINISTRATOR_PERMISSION)
            seen_role_ids.append(role_id)
            await self.execute(
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
                    role["name"],
                    role.get("color"),
                    role.get("position"),
                    permissions,
                    is_admin,
                    int(bool(role.get("managed", False))),
                    int(bool(role.get("mentionable", False))),
                ),
            )

            if is_admin and administrator_role_id:
                await self.execute(
                    """
                    INSERT INTO activity_synced_role_assignments (guild_id, discord_role_id, access_role_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, discord_role_id, access_role_id) DO NOTHING
                    """,
                    (guild_id, role_id, administrator_role_id),
                )

        if seen_role_ids:
            placeholders = ",".join("?" for _ in seen_role_ids)
            await self.execute(
                f"""
                DELETE FROM activity_synced_roles
                WHERE guild_id = ?
                  AND role_id NOT IN ({placeholders})
                """,
                (guild_id, *seen_role_ids),
            )
        await self.commit()
        logger.info("Activity RBAC Discord roles synced for guild_id=%s count=%s", guild_id, len(discord_roles))
        return len(discord_roles)

    async def _ensure_activity_builtin_roles(self, guild_id: int) -> Optional[int]:
        administrator_role_id: Optional[int] = None
        for definition in BUILTIN_ACCESS_ROLES:
            row = await self.fetch_one(
                "SELECT id FROM activity_access_roles WHERE guild_id = ? AND slug = ?",
                (guild_id, definition["slug"]),
            )
            if row:
                role_id = int(row["id"])
            else:
                cursor = await self.execute(
                    """
                    INSERT INTO activity_access_roles (guild_id, slug, name, is_builtin)
                    VALUES (?, ?, ?, 1)
                    """,
                    (guild_id, definition["slug"], definition["name"]),
                )
                role_id = int(cursor.lastrowid)

            for module_key, permission in dict(definition["modules"]).items():
                await self.execute(
                    """
                    INSERT INTO activity_access_role_modules (access_role_id, module_key, permission)
                    VALUES (?, ?, ?)
                    ON CONFLICT(access_role_id, module_key)
                    DO UPDATE SET permission = excluded.permission
                    """,
                    (role_id, module_key, permission),
                )

            if definition["slug"] == "administrator":
                administrator_role_id = role_id

        await self.commit()
        return administrator_role_id

    async def remove_role(self, role_id: int) -> bool:
        """Удалить роль из БД"""
        return await self.delete(where_column="role_id", where_value=role_id)
    
    async def get_auto_assign_count(self) -> int:
        """Получить количество ролей для автовыдачи"""
        result = await self.fetch_one(
            "SELECT COUNT(*) as count FROM roles WHERE guild_id = ? AND is_auto_assign = 1",
            (self._guild_id,),
        )
        return result["count"] if result else 0

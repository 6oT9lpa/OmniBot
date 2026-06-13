from typing import List, Optional, Dict, Any

from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RoleRepository(BaseRepository):
    _TABLE_NAME = "roles"

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
        """Добавить роль"""
        data = {
            "role_id": role_id,
            "guild_id": self._guild_id,
            "name": name,
            "color": color,
            "position": position,
            "is_auto_assign": 1 if is_auto_assign else 0,
            "is_public": 1 if is_public else 0,
            "display_emoji": display_emoji,
            "updated_at": "CURRENT_TIMESTAMP"
        }
        
        logger.info(f"Role added/updated: {name} ({role_id})")
        return await self.upsert(data, conflict_column="role_id")
        
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
        data = []
        for role in discord_roles:
            await self.add_role(
                role_id=role["id"],
                name=role["name"],
                color=role.get("color"),
                position=role.get("position"),
                is_auto_assign=False,
                is_public=True
            )
        
        logger.info(f"Synced {len(discord_roles)} roles from Discord")
        return len(discord_roles)
    
    async def remove_role(self, role_id: int) -> bool:
        """Удалить роль из БД"""
        return await self.delete(where_column="role_id", where_value=role_id)
    
    async def get_auto_assign_count(self) -> int:
        """Получить количество ролей для автовыдачи"""
        return await self.count(
            where_clause="guild_id = ? AND is_auto_assign = 1",
            params=(self.guild_id,)
        )
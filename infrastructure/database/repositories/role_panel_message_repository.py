# infrastructure/database/repositories/role_panel_message_repository.py
from typing import List, Optional, Dict, Any

from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RolePanelMessageRepository(BaseRepository):
    _TABLE_NAME = "role_panel_messages"
    _ALLOWED_COLUMNS = {
        "id", "guild_id", "channel_id", "message_id",
        "embed_title", "embed_description", "embed_color",
        "created_by", "created_at", "updated_at", "is_active",
    }

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def create(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        embed_title: str,
        embed_description: str,
        embed_color: int,
        created_by: int,
    ) -> int:
        data = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "embed_title": embed_title,
            "embed_description": embed_description,
            "embed_color": embed_color,
            "created_by": created_by,
        }
        row_id = await self.insert(data)
        logger.info(f"Created panel: message_id={message_id}, guild={guild_id}")
        return row_id

    async def get_by_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetch_one(
            "SELECT * FROM role_panel_messages WHERE message_id = ? AND is_active = 1",
            (message_id,),
        )

    async def get_by_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        return await self.fetch_all(
            "SELECT * FROM role_panel_messages WHERE guild_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (guild_id,),
        )

    async def delete_by_message(self, message_id: int) -> bool:
        cursor = await self.execute(
            "DELETE FROM role_panel_messages WHERE message_id = ?",
            (message_id,),
        )
        await self.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted panel with message_id={message_id}")
        else:
            logger.warning(f"No panel found to delete with message_id={message_id}")
        return deleted
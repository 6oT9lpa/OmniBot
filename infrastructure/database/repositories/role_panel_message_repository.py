# infrastructure/database/repositories/role_panel_message_repository.py
from typing import List, Optional, Dict, Any

from core.interfaces.repositories import RolePanelMessageRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RolePanelMessageRepository(RolePanelMessageRepositoryInterface, BaseRepository):
    _TABLE_NAME = "role_panel_messages"
    _ALLOWED_COLUMNS = {
        "id", "guild_id", "channel_id", "message_id",
        "embed_title", "embed_description", "embed_color",
        "created_by", "created_at", "updated_at", "is_active",
        "interaction_mode", "view_fingerprint", "last_rendered_fingerprint",
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
        interaction_mode: str = "buttons",
    ) -> int:
        data = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "embed_title": embed_title,
            "embed_description": embed_description,
            "embed_color": embed_color,
            "created_by": created_by,
            "interaction_mode": interaction_mode,
        }
        row_id = await self.insert(data)
        logger.info("Created %s panel: message_id=%s, guild=%s", interaction_mode, message_id, guild_id)
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
            logger.info("Deleted panel with message_id=%s", message_id)
        else:
            logger.warning("No panel found to delete with message_id=%s", message_id)
        return deleted

    async def update_fingerprint(
        self,
        message_id: int,
        *,
        view_fingerprint: Optional[str],
        last_rendered_fingerprint: Optional[str] = None,
    ) -> None:
        fields = ["view_fingerprint = ?"]
        values = [view_fingerprint]

        if last_rendered_fingerprint is not None:
            fields.append("last_rendered_fingerprint = ?")
            values.append(last_rendered_fingerprint)

        values.append(message_id)
        await self.execute(
            f"""
            UPDATE role_panel_messages
            SET {', '.join(fields)}
            WHERE message_id = ?
            """,
            tuple(values),
        )
        await self.commit()

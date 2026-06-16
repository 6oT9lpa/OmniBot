from typing import Optional, Dict, Any, List

from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from core.domain.channel_purpose import ChannelPurpose
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ChannelConfigRepository(BaseRepository):
    _TABLE_NAME = "channel_config"
    _ALLOWED_COLUMNS = {
        "channel_id", "guild_id", "is_ai_whitelisted",
        "welcome_enabled", "slowmode_override", "auto_delete_after",
        "custom_name", "updated_at",
    }

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def get_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetch_one(
            "SELECT * FROM channel_config WHERE channel_id = ?",
            (channel_id,),
        )

    async def get_by_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        return await self.fetch_all(
            "SELECT * FROM channel_config WHERE guild_id = ?",
            (guild_id,),
        )

    async def upsert_channel(
        self,
        channel_id: int,
        guild_id: int,
        *,
        is_ai_whitelisted: bool = False,
        welcome_enabled: bool = True,
        slowmode_override: Optional[int] = None,
        auto_delete_after: Optional[int] = None,
        custom_name: Optional[str] = None,
    ) -> None:
        data: Dict[str, Any] = {
            "channel_id": channel_id,
            "guild_id": guild_id,
            "is_ai_whitelisted": int(is_ai_whitelisted),
            "welcome_enabled": int(welcome_enabled),
            "slowmode_override": slowmode_override,
            "auto_delete_after": auto_delete_after,
            "custom_name": custom_name,
            "updated_at": "CURRENT_TIMESTAMP",
        }
        await self.upsert(data, conflict_column="channel_id")
        logger.debug(f"Upserted channel_config for channel {channel_id}")

    async def set_purpose(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
        channel_id: int,
    ) -> None:
        await self.execute(
            """
            INSERT INTO server_channel_purposes (guild_id, purpose, channel_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, purpose) DO UPDATE SET
                channel_id = excluded.channel_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, purpose.value, channel_id),
        )
        await self.commit()
        logger.info(
            f"Set channel purpose '{purpose.value}' "
            f"-> channel {channel_id} for guild {guild_id}"
        )

    async def remove_purpose(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
    ) -> bool:
        cursor = await self.execute(
            "DELETE FROM server_channel_purposes WHERE guild_id = ? AND purpose = ?",
            (guild_id, purpose.value),
        )
        await self.commit()
        removed = cursor.rowcount > 0
        if removed:
            logger.info(
                f"Removed channel purpose '{purpose.value}' for guild {guild_id}"
            )
        return removed

    async def get_purpose_channel(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
    ) -> Optional[int]:
        row = await self.fetch_one(
            """
            SELECT channel_id FROM server_channel_purposes
            WHERE guild_id = ? AND purpose = ?
            """,
            (guild_id, purpose.value),
        )
        return row["channel_id"] if row else None

    async def get_all_purposes(
        self,
        guild_id: int,
    ) -> Dict[str, int]:
        rows = await self.fetch_all(
            "SELECT purpose, channel_id FROM server_channel_purposes WHERE guild_id = ?",
            (guild_id,),
        )
        return {row["purpose"]: row["channel_id"] for row in rows}
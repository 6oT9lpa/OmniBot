from __future__ import annotations

from typing import Any, Dict, List, Optional

from application.dto.voice_dto import VoiceRoomDTO
from core.interfaces.repositories import VoiceRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VoiceRepository(VoiceRepositoryInterface, BaseRepository):
    _TABLE_NAME = "voice_rooms"
    _ALLOWED_COLUMNS = {
        "channel_id", "guild_id", "owner_id", "admin_id", "name",
        "created_at", "is_persistent",
    }

    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__(db_manager)

    async def create(self, dto: VoiceRoomDTO) -> None:
        """Создать запись о голосовой комнате."""
        try:
            await self.execute(
                """
                INSERT INTO voice_rooms (channel_id, guild_id, owner_id, admin_id, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dto.channel_id,
                    dto.guild_id,
                    dto.owner_id,
                    dto.admin_id,
                    dto.name,
                    dto.created_at.isoformat(timespec="seconds"),
                ),
            )
            await self.commit()
            logger.debug(
                "Voice room created: channel_id=%s owner_id=%s",
                dto.channel_id, dto.owner_id,
            )
        except Exception as exc:
            logger.error("Failed to create voice room: %s", exc)
            raise

    async def delete(self, channel_id: int) -> None:
        """Удалить запись о голосовой комнате."""
        try:
            await self.clear_members(channel_id)
            await self.execute(
                "DELETE FROM voice_rooms WHERE channel_id = ?",
                (channel_id,),
            )
            await self.commit()
            logger.debug("Voice room deleted: channel_id=%s", channel_id)
        except Exception as exc:
            logger.error("Failed to delete voice room channel_id=%s: %s", channel_id, exc)
            raise

    async def get(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Получить запись по ID канала."""
        return await self.fetch_one(
            "SELECT * FROM voice_rooms WHERE channel_id = ?",
            (channel_id,),
        )

    async def get_by_owner(
        self,
        user_id: int,
        guild_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Получить комнату по владельцу."""
        return await self.fetch_one(
            "SELECT * FROM voice_rooms WHERE owner_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )

    async def get_all(self, guild_id: int) -> List[Dict[str, Any]]:
        """Получить все комнаты гильдии."""
        return await self.fetch_all(
            "SELECT * FROM voice_rooms WHERE guild_id = ?",
            (guild_id,),
        )

    async def update_admin(self, channel_id: int, admin_id: Optional[int]) -> None:
        """Обновить владельца комнаты."""
        try:
            await self.execute(
                "UPDATE voice_rooms SET admin_id = ? WHERE channel_id = ?",
                (admin_id, channel_id),
            )
            await self.commit()
            logger.debug(
                "Voice room admin updated: channel_id=%s admin_id=%s",
                channel_id, admin_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to update admin channel_id=%s: %s", channel_id, exc,
            )
            raise

    async def add_member(self, channel_id: int, guild_id: int, user_id: int) -> None:
        try:
            await self.execute(
                """
                INSERT INTO voice_room_members (channel_id, guild_id, user_id)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id, user_id)
                DO UPDATE SET joined_at = datetime('now', 'localtime')
                """,
                (channel_id, guild_id, user_id),
            )
            await self.commit()
            logger.debug("Voice room member tracked: channel_id=%s user_id=%s", channel_id, user_id)
        except Exception as exc:
            logger.error("Failed to track voice room member channel_id=%s user_id=%s: %s", channel_id, user_id, exc)
            raise

    async def remove_member(self, channel_id: int, user_id: int) -> None:
        try:
            await self.execute(
                "DELETE FROM voice_room_members WHERE channel_id = ? AND user_id = ?",
                (channel_id, user_id),
            )
            await self.commit()
            logger.debug("Voice room member untracked: channel_id=%s user_id=%s", channel_id, user_id)
        except Exception as exc:
            logger.error("Failed to untrack voice room member channel_id=%s user_id=%s: %s", channel_id, user_id, exc)
            raise

    async def clear_members(self, channel_id: int) -> None:
        try:
            await self.execute(
                "DELETE FROM voice_room_members WHERE channel_id = ?",
                (channel_id,),
            )
            await self.commit()
            logger.debug("Voice room members cleared: channel_id=%s", channel_id)
        except Exception as exc:
            logger.error("Failed to clear voice room members channel_id=%s: %s", channel_id, exc)
            raise

    async def get_member_ids(self, channel_id: int) -> List[int]:
        rows = await self.fetch_all(
            "SELECT user_id FROM voice_room_members WHERE channel_id = ? ORDER BY joined_at ASC, user_id ASC",
            (channel_id,),
        )
        member_ids = [int(row["user_id"]) for row in rows]
        logger.debug("Voice room members loaded: channel_id=%s count=%s", channel_id, len(member_ids))
        return member_ids

    async def set_persistent(self, channel_id: int, persistent: bool) -> None:
        """Установить флаг постоянства комнаты."""
        try:
            await self.execute(
                "UPDATE voice_rooms SET is_persistent = ? WHERE channel_id = ?",
                (int(persistent), channel_id),
            )
            await self.commit()
        except Exception as exc:
            logger.error(
                "Failed to set persistent channel_id=%s: %s", channel_id, exc,
            )
            raise

    async def set_config(self, key: str, value: str) -> None:
        """Сохранить конфигурацию."""
        try:
            await self.execute(
                "INSERT OR REPLACE INTO voice_config (key, value) VALUES (?, ?)",
                (key, value),
            )
            await self.commit()
            logger.debug("Voice config set: key=%s", key)
        except Exception as exc:
            logger.error("Failed to set voice config key=%s: %s", key, exc)
            raise

    async def get_config(self, key: str) -> Optional[str]:
        """Получить конфигурацию."""
        row = await self.fetch_one(
            "SELECT value FROM voice_config WHERE key = ?",
            (key,),
        )
        return row["value"] if row else None

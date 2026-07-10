from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.interfaces.repositories import StatsRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)

_MSK = timezone(timedelta(hours=3))


def _msk_now() -> str:
    return datetime.now(_MSK).strftime("%Y-%m-%dT%H:%M:%S")


def _msk_cutoff(days: int) -> str:
    return (datetime.now(_MSK) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


class StatsRepository(StatsRepositoryInterface, BaseRepository):
    _TABLE_NAME = "user_stats"

    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__(db_manager)

    async def get_or_create(self, user_id: int, guild_id: int) -> None:
        """Создать запись пользователя, если не существует."""
        existing = await self.fetch_one(
            "SELECT user_id FROM user_stats WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        if existing:
            return

        try:
            await self.execute(
                """
                INSERT INTO user_stats
                    (user_id, guild_id, messages_count, voice_minutes, warnings_count, joined_at)
                VALUES (?, ?, 0, 0, 0, ?)
                """,
                (user_id, guild_id, _msk_now()),
            )
            await self.commit()
            logger.debug("Created user_stats for user_id=%s guild_id=%s", user_id, guild_id)
        except Exception as exc:
            logger.error(
                "Failed to create user_stats user_id=%s guild_id=%s: %s",
                user_id, guild_id, exc,
            )
            raise

    async def increment_messages(self, user_id: int, guild_id: int) -> None:
        """Увеличить счётчик сообщений на 1."""
        await self.get_or_create(user_id, guild_id)
        now = _msk_now()
        await self.execute(
            """
            UPDATE user_stats
            SET messages_count = messages_count + 1,
                last_message = ?,
                updated_at = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (now, now, guild_id, user_id),
        )
        await self.commit()

    async def add_voice_minutes(self, user_id: int, guild_id: int, minutes: int) -> None:
        """Добавить минуты голосовой активности."""
        if minutes <= 0:
            return
        await self.get_or_create(user_id, guild_id)
        await self.execute(
            """
            UPDATE user_stats
            SET voice_minutes = voice_minutes + ?,
                updated_at = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (minutes, _msk_now(), guild_id, user_id),
        )
        await self.commit()

    async def increment_warnings(self, user_id: int, guild_id: int) -> None:
        """Увеличить счётчик предупреждений."""
        await self.get_or_create(user_id, guild_id)
        await self.execute(
            """
            UPDATE user_stats
            SET warnings_count = warnings_count + 1,
                updated_at = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (_msk_now(), guild_id, user_id),
        )
        await self.commit()

    async def log_message_to_history(
        self,
        message_id: int,
        user_id: int,
        guild_id: int,
        channel_id: int,
    ) -> None:
        """Записать сообщение в таблицу messages."""
        try:
            await self.execute(
                """
                INSERT INTO messages (id, user_id, guild_id, channel_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (message_id, user_id, guild_id, channel_id, _msk_now()),
            )
            await self.commit()
        except Exception as exc:
            logger.error(
                "Failed to log message_id=%s to history: %s", message_id, exc,
            )
            raise

    async def get_user_stats(
        self,
        user_id: int,
        guild_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Получить статистику пользователя."""
        return await self.fetch_one(
            """
            SELECT user_id, messages_count, voice_minutes, warnings_count,
                   joined_at, last_message
            FROM user_stats
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id),
        )

    async def get_server_stats(self, guild_id: int, period: int) -> Dict[str, Any]:
        """Получить общую статистику сервера за период."""
        cutoff = _msk_cutoff(period)

        row = await self.fetch_one(
            """
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(DISTINCT channel_id) as active_channels
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            """,
            (guild_id, cutoff),
        )
        total = row["total_messages"] or 0
        active_users = row["active_users"] or 0
        active_channels = row["active_channels"] or 0

        avg_row = await self.fetch_one(
            "SELECT COUNT(*) * 1.0 / ? as avg_per_day FROM messages WHERE guild_id = ? AND timestamp >= ? AND deleted = 0",
            (period, guild_id, cutoff),
        )
        avg_per_day = round(avg_row["avg_per_day"] or 0, 1)

        top_user = await self.fetch_one(
            """
            SELECT user_id, COUNT(*) as count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 1
            """,
            (guild_id, cutoff),
        )
        top_user_id = top_user["user_id"] if top_user else None
        top_user_count = top_user["count"] if top_user else 0

        top_channel = await self.fetch_one(
            """
            SELECT channel_id, COUNT(*) as count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY channel_id
            ORDER BY count DESC
            LIMIT 1
            """,
            (guild_id, cutoff),
        )
        top_channel_id = top_channel["channel_id"] if top_channel else None
        top_channel_count = top_channel["count"] if top_channel else 0

        top_hour = await self.fetch_one(
            """
            SELECT EXTRACT(HOUR FROM timestamp)::integer AS hour, COUNT(*) AS count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 1
            """,
            (guild_id, cutoff),
        )
        top_hour_val = top_hour["hour"] if top_hour else None
        top_hour_count = top_hour["count"] if top_hour else 0

        daily = await self.fetch_all(
            """
            SELECT 
                CASE EXTRACT(DOW FROM timestamp)::integer
                    WHEN 0 THEN 'Вс'
                    WHEN 1 THEN 'Пн'
                    WHEN 2 THEN 'Вт'
                    WHEN 3 THEN 'Ср'
                    WHEN 4 THEN 'Чт'
                    WHEN 5 THEN 'Пт'
                    WHEN 6 THEN 'Сб'
                END as day,
                COUNT(*) as count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY EXTRACT(DOW FROM timestamp)::integer
            ORDER BY EXTRACT(DOW FROM timestamp)::integer
            """,
            (guild_id, cutoff),
        )

        voice_stats = await self.fetch_one(
            """
            SELECT 
                COUNT(DISTINCT user_id) as voice_users,
                SUM(voice_minutes) as total_voice_minutes
            FROM user_stats
            WHERE guild_id = ? AND voice_minutes > 0
            """,
            (guild_id,),
        )
        voice_users = voice_stats["voice_users"] or 0
        total_voice_minutes = voice_stats["total_voice_minutes"] or 0

        top_voice = await self.fetch_all(
            """
            SELECT user_id, voice_minutes
            FROM user_stats
            WHERE guild_id = ? AND voice_minutes > 0
            ORDER BY voice_minutes DESC
            LIMIT 3
            """,
            (guild_id,),
        )

        return {
            "total_messages": total,
            "active_users": active_users,
            "active_channels": active_channels,
            "avg_per_day": avg_per_day,
            "top_user_id": top_user_id,
            "top_user_count": top_user_count,
            "top_channel_id": top_channel_id,
            "top_channel_count": top_channel_count,
            "top_hour": top_hour_val,
            "top_hour_count": top_hour_count,
            "daily_stats": daily,
            "voice_users": voice_users,
            "total_voice_minutes": total_voice_minutes,
            "top_voice": top_voice,
        }

    async def get_top_channels(
        self,
        guild_id: int,
        days: int = 7,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Топ каналов по числу сообщений за N дней."""
        return await self.fetch_all(
            """
            SELECT channel_id, COUNT(*) as count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY channel_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (guild_id, _msk_cutoff(days), limit),
        )

    async def get_activity_by_hour(
        self,
        guild_id: int,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Активность по часам (МСК)."""
        return await self.fetch_all(
            """
            SELECT EXTRACT(HOUR FROM timestamp)::integer AS hour,
                   COUNT(*) AS count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY hour
            ORDER BY hour
            """,
            (guild_id, _msk_cutoff(days)),
        )

    async def get_leaderboard(
        self,
        guild_id: int,
        days: int = 7,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Топ участников по числу сообщений за N дней."""
        return await self.fetch_all(
            """
            SELECT user_id, COUNT(*) as count
            FROM messages
            WHERE guild_id = ? AND timestamp >= ? AND deleted = 0
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (guild_id, _msk_cutoff(days), limit),
        )

    async def reset_user_stats(self, user_id: int, guild_id: int) -> None:
        """Сбросить статистику пользователя."""
        await self.execute(
            """
            UPDATE user_stats
            SET messages_count = 0,
                voice_minutes = 0,
                warnings_count = 0,
                last_message = NULL,
                updated_at = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (_msk_now(), guild_id, user_id),
        )
        await self.commit()

    async def delete_user_stats(self, user_id: int, guild_id: int) -> None:
        """Удалить запись пользователя."""
        await self.execute(
            "DELETE FROM user_stats WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.commit()

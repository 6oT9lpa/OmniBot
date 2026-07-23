from datetime import datetime

from core.interfaces.repositories.member_join_history_repository_interface import MemberJoinHistoryRepositoryInterface
from infrastructure.database.repositories.base import BaseRepository


class MemberJoinHistoryRepository(BaseRepository, MemberJoinHistoryRepositoryInterface):
    async def record_join(self, guild_id: int, user_id: int, joined_at: datetime) -> bool:
        existing = await self.fetch_one(
            "SELECT first_joined_at FROM member_join_history WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.execute_write(
            """
            INSERT INTO member_join_history (guild_id, user_id, first_joined_at, latest_joined_at, join_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET
                latest_joined_at = excluded.latest_joined_at,
                join_count = member_join_history.join_count + 1
            WHERE member_join_history.latest_joined_at <> excluded.latest_joined_at
            """,
            (guild_id, user_id, joined_at, joined_at),
        )
        return existing is None

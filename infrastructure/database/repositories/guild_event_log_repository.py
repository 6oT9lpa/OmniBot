from datetime import datetime
from typing import List, Optional, Dict, Any

from core.domain.value_objects import EventType

from application.dto.logging_dto import GuildEventLogDTO
from core.interfaces.repositories import GuildEventLogRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class GuildEventLogRepository(GuildEventLogRepositoryInterface, BaseRepository):
    _TABLE_NAME = "guild_event_logs"
    _ALLOWED_COLUMNS = {
        "guild_id", "channel_id", "actor_id", "actor_name", "target_id", "target_name",
        "event_type", "details", "created_at", "retention_until",
    }

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def add(self, dto: GuildEventLogDTO) -> int:
        data = dto.to_db()
        row_id = await self.insert(data)
        logger.debug("Inserted guild event log id=%s event=%s", row_id, dto.event_type)
        return row_id

    async def get(self, log_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetch_one("SELECT * FROM guild_event_logs WHERE id = ?", (log_id,))

    async def list_recent(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        return await self.fetch_all(
            """
            SELECT * FROM guild_event_logs
            WHERE guild_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (guild_id, limit),
        )

    async def cleanup_expired(self, cutoff_iso: str) -> int:
        cursor = await self.execute(
            "DELETE FROM guild_event_logs WHERE retention_until IS NOT NULL AND retention_until < ?",
            (cutoff_iso,),
        )
        await self.commit()
        return cursor.rowcount

    async def log_event(
        self,
        guild_id: int,
        event_type: EventType,
        data: Dict[str, Any],
        *,
        user_id: Optional[int] = None,
        target_id: Optional[int] = None,
    ) -> int:
        return await self.add(
            GuildEventLogDTO(
                guild_id=guild_id,
                event_type=event_type.value,
                created_at=datetime.now(),
                actor_id=user_id,
                actor_name=data.get("actor_name") or data.get("user_name"),
                target_id=target_id,
                target_name=data.get("target_name"),
                details=str(data),
            )
        )

    async def get_events(
        self,
        guild_id: int,
        event_type: Optional[EventType] = None,
        *,
        limit: int = 100,
        since: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        clauses = ["guild_id = ?"]
        params: List[Any] = [guild_id]
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type.value)
        if user_id is not None:
            clauses.append("(actor_id = ? OR target_id = ?)")
            params.extend([user_id, user_id])
        if since is not None:
            clauses.append("created_at >= ?")
            params.append(since.isoformat(timespec="seconds"))
        params.append(limit)
        return await self.fetch_all(
            f"""
            SELECT * FROM guild_event_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        )

    async def get_member_join_leave_stats(
        self,
        guild_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        row = await self.fetch_one(
            """
            SELECT
                SUM(CASE WHEN event_type = 'member_join' THEN 1 ELSE 0 END) as joins,
                SUM(CASE WHEN event_type = 'member_leave' THEN 1 ELSE 0 END) as leaves
            FROM guild_event_logs
            WHERE guild_id = ?
              AND created_at >= datetime('now', 'localtime', ?)
            """,
            (guild_id, f"-{days} days"),
        )
        return {
            "joins": int(row.get("joins") or 0),
            "leaves": int(row.get("leaves") or 0),
        }

    async def get_role_change_history(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        return await self.fetch_all(
            """
            SELECT * FROM guild_event_logs
            WHERE target_id = ? AND event_type IN ('role_create', 'role_update', 'role_delete')
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

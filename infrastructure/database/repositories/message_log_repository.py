from datetime import datetime
from typing import List, Optional, Dict, Any

from application.dto.logging_dto import MessageLogDTO
from core.interfaces.repositories import MessageLogRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MessageLogRepository(MessageLogRepositoryInterface, BaseRepository):
    _TABLE_NAME = "message_logs"
    _ALLOWED_COLUMNS = {
        "guild_id", "channel_id", "message_id", "author_id", "author_name",
        "content", "event_type", "created_at", "retention_until",
    }

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def add(self, dto: MessageLogDTO) -> int:
        data = dto.to_db()
        row_id = await self.insert(data)
        logger.debug("Inserted message log id=%s event=%s", row_id, dto.event_type)
        return row_id

    async def get(self, log_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetch_one("SELECT * FROM message_logs WHERE id = ?", (log_id,))

    async def list_recent(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        return await self.fetch_all(
            """
            SELECT * FROM message_logs
            WHERE guild_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (guild_id, limit),
        )

    async def cleanup_expired(self, cutoff_iso: str) -> int:
        cursor = await self.execute(
            "DELETE FROM message_logs WHERE retention_until IS NOT NULL AND retention_until < ?",
            (cutoff_iso,),
        )
        await self.commit()
        return cursor.rowcount

    async def save_message(
        self,
        message_id: int,
        channel_id: int,
        guild_id: int,
        author_id: int,
        content: str,
        *,
        is_edited: bool = False,
        is_deleted: bool = False,
        edited_at: Optional[datetime] = None,
        ai_flagged: bool = False,
        ai_reason: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> None:
        existing = await self.get_message_by_id(message_id)
        event_type = "message_delete" if is_deleted else "message_edit" if is_edited else "message"
        if existing:
            data = {
                "channel_id": channel_id,
                "author_id": author_id,
                "content": content,
                "event_type": event_type,
            }
            await self.update(data, "id", existing["id"])
            return

        await self.add(
            MessageLogDTO(
                guild_id=guild_id,
                message_id=message_id,
                channel_id=channel_id,
                author_id=author_id,
                author_name=str(author_id),
                content=content,
                created_at=datetime.now(),
                event_type=event_type,
                is_edited=is_edited,
                is_deleted=is_deleted,
                ai_flagged=ai_flagged,
                retention_until=None,
            )
        )

    async def mark_as_deleted(
        self,
        message_id: int,
        deleted_at: Optional[datetime] = None,
    ) -> bool:
        cursor = await self.execute(
            "UPDATE message_logs SET event_type = 'message_delete' WHERE message_id = ?",
            (message_id,),
        )
        await self.commit()
        return cursor.rowcount > 0

    async def mark_as_edited(
        self,
        message_id: int,
        new_content: str,
        edited_at: datetime,
    ) -> bool:
        cursor = await self.execute(
            """
            UPDATE message_logs
            SET content = ?, event_type = 'message_edit'
            WHERE message_id = ?
            """,
            (new_content, message_id),
        )
        await self.commit()
        return cursor.rowcount > 0

    async def get_message_history(
        self,
        channel_id: int,
        limit: int = 100,
        *,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        author_id: Optional[int] = None,
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        clauses = ["channel_id = ?"]
        params: List[Any] = [channel_id]
        if not include_deleted:
            clauses.append("event_type != 'message_delete'")
        if author_id is not None:
            clauses.append("author_id = ?")
            params.append(author_id)
        if before is not None:
            clauses.append("created_at < ?")
            params.append(before.isoformat(timespec="seconds"))
        if after is not None:
            clauses.append("created_at > ?")
            params.append(after.isoformat(timespec="seconds"))
        params.append(limit)
        return await self.fetch_all(
            f"""
            SELECT * FROM message_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        )

    async def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetch_one("SELECT * FROM message_logs WHERE message_id = ?", (message_id,))

    async def get_user_messages_count(
        self,
        user_id: int,
        guild_id: int,
        *,
        since: Optional[datetime] = None,
    ) -> int:
        clauses = ["guild_id = ?", "author_id = ?", "event_type = 'message'"]
        params: List[Any] = [guild_id, user_id]
        if since is not None:
            clauses.append("created_at >= ?")
            params.append(since.isoformat(timespec="seconds"))
        params.append(1)
        row = await self.fetch_one(
            f"""
            SELECT COUNT(*) as count FROM message_logs
            WHERE {' AND '.join(clauses)}
            LIMIT ?
            """,
            tuple(params),
        )
        return int(row["count"]) if row else 0
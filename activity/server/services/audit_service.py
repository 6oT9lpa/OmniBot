from typing import Optional

from activity.server.dependencies import get_db
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityAuditService:
    async def log_action(
        self,
        *,
        guild_id: int,
        event_type: str,
        details: str,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
    ) -> None:
        logger.info(
            "Writing Activity audit event guild_id=%s event_type=%s actor_id=%s target_id=%s",
            guild_id,
            event_type,
            actor_id,
            target_id,
        )
        await get_db().execute(
            """
            INSERT INTO guild_event_logs (
                guild_id,
                actor_id,
                actor_name,
                target_id,
                target_name,
                event_type,
                details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, actor_id, actor_name, target_id, target_name, event_type, details),
        )
        await get_db().commit()
        logger.info("Activity audit event written guild_id=%s event_type=%s", guild_id, event_type)

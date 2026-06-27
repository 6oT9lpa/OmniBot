from typing import Optional

from activity.server.dependencies import get_db


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

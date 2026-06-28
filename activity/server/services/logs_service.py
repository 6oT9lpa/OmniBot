from typing import Any, Optional

from activity.server.dependencies import get_db
from activity.server.services.access_service import ActivityAccessService
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class LogsService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()

    async def list_logs(
        self,
        guild_id: int,
        source: str,
        event_type: Optional[str],
        query: str,
        limit: int,
        access_token: str,
    ) -> dict[str, list[dict[str, Any]]]:
        logger.info("Listing Activity logs guild_id=%s source=%s event_type=%s limit=%s", guild_id, source, event_type, limit)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "logs")
        normalized_source = source.strip().lower() or "all"
        return {
            "messages": [] if normalized_source in {"audit", "activity", "moderator", "welcome", "channel"} else await self._query_message_logs(guild_id, event_type, query, limit),
            "audit": [] if normalized_source == "messages" else await self._query_audit_logs(guild_id, normalized_source, event_type, query, limit),
        }

    async def _query_message_logs(
        self,
        guild_id: int,
        event_type: Optional[str],
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = ["guild_id = ?"]
        params: list[Any] = [guild_id]
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if query.strip():
            clauses.append("(content LIKE ? OR author_name LIKE ?)")
            like = f"%{query.strip()}%"
            params.extend([like, like])
        params.append(limit)
        return await get_db().fetch_all(
            f"""
            SELECT * FROM message_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        )

    async def _query_audit_logs(
        self,
        guild_id: int,
        source: str,
        event_type: Optional[str],
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = ["guild_id = ?"]
        params: list[Any] = [guild_id]
        source_prefixes = {
            "moderator": ["moderation_", "punishment_", "auto_moderation_"],
            "welcome": ["welcome_", "member_"],
            "channel": ["channel_"],
            "activity": ["activity_"],
        }
        prefixes = source_prefixes.get(source, [])
        if prefixes:
            clauses.append("(" + " OR ".join("event_type LIKE ?" for _ in prefixes) + ")")
            params.extend(f"{prefix}%" for prefix in prefixes)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if query.strip():
            clauses.append("(details LIKE ? OR actor_name LIKE ? OR target_name LIKE ?)")
            like = f"%{query.strip()}%"
            params.extend([like, like, like])
        params.append(limit)
        return await get_db().fetch_all(
            f"""
            SELECT * FROM guild_event_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        )

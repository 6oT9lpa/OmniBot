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

    async def list_actors(self, guild_id: int, access_token: str) -> list[dict[str, str]]:
        logger.info("Listing Activity log actors guild_id=%s", guild_id)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "logs")
        actors: dict[str, str] = {}
        for row in await self._safe_fetch_all(
            """
            SELECT actor_id AS id, actor_name AS name FROM guild_event_logs
            WHERE guild_id = ? AND actor_id IS NOT NULL
            UNION
            SELECT author_id AS id, author_name AS name FROM message_logs
            WHERE guild_id = ? AND author_id IS NOT NULL
            ORDER BY name
            """,
            (guild_id, guild_id),
            "log actor list",
        ):
            actor_id = str(row.get("id") or "")
            if actor_id:
                actors[actor_id] = str(row.get("name") or actor_id)
        return [{"id": actor_id, "name": name} for actor_id, name in actors.items()]

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
        return await self._safe_fetch_all(
            f"""
            SELECT * FROM message_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
            "message logs",
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
        return await self._safe_fetch_all(
            f"""
            SELECT * FROM guild_event_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
            "audit logs",
        )

    async def _safe_fetch_all(self, query: str, params: tuple[Any, ...], label: str) -> list[dict[str, Any]]:
        try:
            return await get_db().fetch_all(query, params)
        except Exception as exc:
            logger.warning("Activity %s unavailable error=%s", label, exc)
            return []

from typing import Any, Optional

from activity.server.dependencies import get_db
from activity.server.schemas.rbac import (
    ActivityAuditEvent,
    ActivityAuditPage,
    ActivityDashboardMetric,
    ActivityDashboardResponse,
)
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.discord_service import DiscordService
from activity.server.utils.rbac import MODULE_ORDER
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityDashboardService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._discord = DiscordService()

    async def get_dashboard(self, guild_id: int, access_token: str) -> ActivityDashboardResponse:
        logger.info("Loading Activity dashboard guild_id=%s", guild_id)
        _, access = await self._access_service.ensure_module_access(access_token, str(guild_id), "dashboard")
        metrics = await self._build_metrics(guild_id, access)
        audit = await self._query_audit_events(guild_id, limit=5, offset=0)
        return ActivityDashboardResponse(metrics=metrics, audit=audit["items"])

    async def list_audit_events(
        self,
        guild_id: int,
        access_token: str,
        *,
        query: str = "",
        actor: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> ActivityAuditPage:
        logger.info("Listing Activity audit events guild_id=%s limit=%s offset=%s", guild_id, limit, offset)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "logs")
        return await self._query_audit_events(
            guild_id,
            query=query,
            actor=actor,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    async def _build_metrics(self, guild_id: int, access: dict[str, Any]) -> ActivityDashboardMetric:
        modules_ready = len(access.get("available_modules", []))
        modules_total = len(MODULE_ORDER)
        ai_checks_today = await self._count_messages_today(guild_id)
        ai_flagged_today = await self._count_messages_today(guild_id, flagged=True)
        creator_sources = await self._count_creator_sources(guild_id)
        return ActivityDashboardMetric(
            modules_ready=modules_ready,
            modules_total=modules_total,
            ai_checks_today=ai_checks_today,
            ai_flagged_today=ai_flagged_today,
            creator_sources=creator_sources,
            bot_latency_ms=await self._discord.measure_latency(),
        )

    async def _count_messages_today(self, guild_id: int, flagged: Optional[bool] = None) -> int:
        clauses = ["guild_id = ?", "date(timestamp) = date('now', 'localtime')"]
        params: list[Any] = [guild_id]
        if flagged is not None:
            clauses.append("ai_flagged = ?")
            params.append(1 if flagged else 0)
        row = await get_db().fetch_one(
            f"SELECT COUNT(*) AS total FROM messages WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
        return int(row["total"] if row else 0)

    async def _count_creator_sources(self, guild_id: int) -> int:
        row = await get_db().fetch_one(
            "SELECT COUNT(*) AS total FROM streamers WHERE guild_id = ?",
            (guild_id,),
        )
        return int(row["total"] if row else 0)

    async def _query_audit_events(
        self,
        guild_id: int,
        *,
        query: str = "",
        actor: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int,
        offset: int,
    ) -> ActivityAuditPage:
        clauses = ["guild_id = ?"]
        params: list[Any] = [guild_id]

        if query.strip():
            like = f"%{query.strip()}%"
            clauses.append("(event_type LIKE ? OR details LIKE ? OR target_name LIKE ?)")
            params.extend([like, like, like])
        if actor.strip():
            like = f"%{actor.strip()}%"
            clauses.append("(actor_name LIKE ? OR CAST(actor_id AS TEXT) LIKE ?)")
            params.extend([like, like])
        if date_from.strip():
            clauses.append("created_at >= ?")
            params.append(date_from.strip())
        if date_to.strip():
            clauses.append("created_at <= ?")
            params.append(date_to.strip())

        where_sql = " AND ".join(clauses)
        total_row = await get_db().fetch_one(
            f"SELECT COUNT(*) AS total FROM guild_event_logs WHERE {where_sql}",
            tuple(params),
        )
        rows = await get_db().fetch_all(
            f"""
            SELECT id, guild_id, actor_id, actor_name, target_id, target_name, event_type, details, created_at
            FROM guild_event_logs
            WHERE {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        return ActivityAuditPage(
            items=[ActivityAuditEvent(**row) for row in rows],
            total=int(total_row["total"] if total_row else 0),
            limit=limit,
            offset=offset,
        )

from typing import Any

from activity.server.dependencies import get_db
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.discord_service import DiscordService
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityStatsService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._discord = DiscordService()

    async def get_server_stats(self, guild_id: int, period: int, access_token: str) -> dict[str, Any]:
        logger.info("Loading Activity server stats guild_id=%s period=%s", guild_id, period)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "server-stats")
        return {
            "summary": await self._query_server_stats(guild_id, period),
            "channels": await self._query_channel_stats(guild_id, period),
            "hourly": await self._query_hourly_stats(guild_id, period),
            "daily": await self._query_daily_stats(guild_id, min(period, 30)),
        }

    async def search_user_stats(self, guild_id: int, query: str, access_token: str) -> list[dict[str, Any]]:
        logger.info("Searching Activity user stats guild_id=%s query=%s", guild_id, query)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "server-stats")
        members = await self._discord.search_members(str(guild_id), query, 10)
        stats = []
        for member in members:
            row = await get_db().fetch_one(
                "SELECT * FROM user_stats WHERE guild_id = ? AND user_id = ?",
                (guild_id, int(member.id)),
            )
            stats.append({"member": member.model_dump(), "stats": row or self._empty_user_stats(guild_id, int(member.id))})
        return stats

    def _empty_user_stats(self, guild_id: int, user_id: int) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "guild_id": guild_id,
            "messages_count": 0,
            "voice_minutes": 0,
            "warnings_count": 0,
            "last_message": None,
            "joined_at": None,
        }

    async def _query_server_stats(self, guild_id: int, period: int) -> dict[str, Any]:
        cutoff = f"-{period} days"
        messages = await self._fetch_one_or_empty(
            """
            SELECT COUNT(*) AS total_messages,
                   COUNT(DISTINCT user_id) AS active_users,
                   COUNT(DISTINCT channel_id) AS active_channels
            FROM messages
            WHERE guild_id = ? AND timestamp >= CURRENT_TIMESTAMP + (?::interval) AND deleted = 0
            """,
            (guild_id, cutoff),
            "server message stats",
        )
        voice = await self._fetch_one_or_empty(
            """
            SELECT COUNT(DISTINCT user_id) AS voice_users,
                   SUM(voice_minutes) AS total_voice_minutes
            FROM user_stats
            WHERE guild_id = ? AND voice_minutes > 0
            """,
            (guild_id,),
            "server voice stats",
        )
        joins = await self._fetch_one_or_empty(
            """
            SELECT SUM(CASE WHEN event_type = 'member_join' THEN 1 ELSE 0 END) AS joins,
                   SUM(CASE WHEN event_type = 'member_leave' THEN 1 ELSE 0 END) AS leaves
            FROM guild_event_logs
            WHERE guild_id = ? AND created_at >= CURRENT_TIMESTAMP + (?::interval)
            """,
            (guild_id, cutoff),
            "server join stats",
        )
        return {
            **(messages or {}),
            **{f"voice_{key}": value for key, value in (voice or {}).items()},
            **(joins or {}),
            "period_days": period,
        }

    async def _query_channel_stats(self, guild_id: int, period: int) -> list[dict[str, Any]]:
        rows = await self._fetch_all_or_empty(
            """
            SELECT channel_id, COUNT(*) AS messages
            FROM messages
            WHERE guild_id = ? AND timestamp >= CURRENT_TIMESTAMP + (?::interval) AND deleted = 0
            GROUP BY channel_id
            ORDER BY messages DESC
            LIMIT 100
            """,
            (guild_id, f"-{period} days"),
            "channel message stats",
        )
        channels = {
            channel["id"]: channel
            for channel in await self._discord.safe_bot_request("GET", f"/guilds/{guild_id}/channels") or []
        }
        return [
            {
                **row,
                "channel_name": channels.get(str(row["channel_id"]), {}).get("name", str(row["channel_id"])),
            }
            for row in rows
        ]

    async def _query_hourly_stats(self, guild_id: int, period: int) -> list[dict[str, int]]:
        rows = await self._fetch_all_or_empty(
            """
            SELECT EXTRACT(HOUR FROM timestamp)::integer AS hour, COUNT(*) AS count
            FROM messages
            WHERE guild_id = ? AND timestamp >= CURRENT_TIMESTAMP + (?::interval) AND deleted = 0
            GROUP BY hour
            ORDER BY hour
            """,
            (guild_id, f"-{period} days"),
            "hourly message stats",
        )
        values = {hour: 0 for hour in range(24)}
        for row in rows:
            values[int(row["hour"])] = int(row["count"])
        return [{"hour": hour, "count": count} for hour, count in values.items()]

    async def _query_daily_stats(self, guild_id: int, days: int) -> list[dict[str, Any]]:
        rows = await self._fetch_all_or_empty(
            """
            SELECT timestamp::date AS day, COUNT(*) AS count
            FROM messages
            WHERE guild_id = ? AND timestamp >= CURRENT_TIMESTAMP + (?::interval) AND deleted = 0
            GROUP BY day
            ORDER BY day
            """,
            (guild_id, f"-{days - 1} days"),
            "daily message stats",
        )
        counts = {str(row["day"]): int(row["count"]) for row in rows}
        series = []
        for index in range(days - 1, -1, -1):
            day_row = await get_db().fetch_one("SELECT (CURRENT_DATE + (?::interval))::date AS day", (f"-{index} days",))
            day = str(day_row["day"])
            series.append({"date": day, "count": counts.get(day, 0)})
        return series

    async def _fetch_one_or_empty(self, query: str, params: tuple[Any, ...], label: str) -> dict[str, Any]:
        try:
            return await get_db().fetch_one(query, params) or {}
        except Exception as exc:
            logger.warning("Activity %s unavailable error=%s", label, exc)
            return {}

    async def _fetch_all_or_empty(self, query: str, params: tuple[Any, ...], label: str) -> list[dict[str, Any]]:
        try:
            return await get_db().fetch_all(query, params)
        except Exception as exc:
            logger.warning("Activity %s unavailable error=%s", label, exc)
            return []

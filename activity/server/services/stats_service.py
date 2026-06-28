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
            stats.append({"member": member.model_dump(), "stats": row})
        return stats

    async def _query_server_stats(self, guild_id: int, period: int) -> dict[str, Any]:
        cutoff = f"-{period} days"
        messages = await get_db().fetch_one(
            """
            SELECT COUNT(*) AS total_messages,
                   COUNT(DISTINCT user_id) AS active_users,
                   COUNT(DISTINCT channel_id) AS active_channels
            FROM messages
            WHERE guild_id = ? AND timestamp >= datetime('now', 'localtime', ?) AND deleted = 0
            """,
            (guild_id, cutoff),
        )
        voice = await get_db().fetch_one(
            """
            SELECT COUNT(DISTINCT user_id) AS voice_users,
                   SUM(voice_minutes) AS total_voice_minutes
            FROM user_stats
            WHERE guild_id = ? AND voice_minutes > 0
            """,
            (guild_id,),
        )
        joins = await get_db().fetch_one(
            """
            SELECT SUM(CASE WHEN event_type = 'member_join' THEN 1 ELSE 0 END) AS joins,
                   SUM(CASE WHEN event_type = 'member_leave' THEN 1 ELSE 0 END) AS leaves
            FROM guild_event_logs
            WHERE guild_id = ? AND created_at >= datetime('now', 'localtime', ?)
            """,
            (guild_id, cutoff),
        )
        return {
            **(messages or {}),
            **{f"voice_{key}": value for key, value in (voice or {}).items()},
            **(joins or {}),
            "period_days": period,
        }

    async def _query_channel_stats(self, guild_id: int, period: int) -> list[dict[str, Any]]:
        rows = await get_db().fetch_all(
            """
            SELECT channel_id, COUNT(*) AS messages
            FROM messages
            WHERE guild_id = ? AND timestamp >= datetime('now', 'localtime', ?) AND deleted = 0
            GROUP BY channel_id
            ORDER BY messages DESC
            LIMIT 100
            """,
            (guild_id, f"-{period} days"),
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
        rows = await get_db().fetch_all(
            """
            SELECT CAST(substr(timestamp, 12, 2) AS INTEGER) AS hour, COUNT(*) AS count
            FROM messages
            WHERE guild_id = ? AND timestamp >= datetime('now', 'localtime', ?) AND deleted = 0
            GROUP BY hour
            ORDER BY hour
            """,
            (guild_id, f"-{period} days"),
        )
        values = {hour: 0 for hour in range(24)}
        for row in rows:
            values[int(row["hour"])] = int(row["count"])
        return [{"hour": hour, "count": count} for hour, count in values.items()]

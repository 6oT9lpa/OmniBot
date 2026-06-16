from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import disnake

from core.interfaces.repositories.stats_repository_interface import StatsRepositoryInterface
from core.interfaces.services.stats_service_interface import StatsServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)
MSK = timezone(timedelta(hours=3))


class StatsService(StatsServiceInterface):
    def __init__(self, stats_repo: StatsRepositoryInterface) -> None:
        self._repo = stats_repo
        self._bot: Optional[disnake.Client] = None

    def set_bot(self, bot: disnake.Client) -> None:
        self._bot = bot

    async def log_message(self, message: disnake.Message) -> None:
        if not message.guild or message.author.bot:
            return

        try:
            await self._repo.increment_messages(message.author.id, message.guild.id)
            await self._repo.log_message_to_history(
                message.id,
                message.author.id,
                message.guild.id,
                message.channel.id,
            )
            logger.debug("Logged message %s from user %s", message.id, message.author.id)
        except Exception as exc:
            logger.error("Error logging message: %s", exc)

    async def log_voice_activity(self, member: disnake.Member, joined_at: datetime) -> None:
        if not member.guild or member.bot:
            return

        duration = datetime.now(MSK) - joined_at
        minutes = int(duration.total_seconds() // 60)
        if minutes <= 0:
            return

        try:
            await self._repo.add_voice_minutes(member.id, member.guild.id, minutes)
            logger.debug("Logged voice activity for %s: %s min", member.id, minutes)
        except Exception as exc:
            logger.error("Error logging voice activity: %s", exc)

    async def get_user_stats(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        return await self._repo.get_user_stats(user_id, guild_id)

    async def get_server_stats(self, guild_id: int, period: int = 7) -> Dict[str, Any]:
        return await self._repo.get_server_stats(guild_id, period)

    async def get_top_channels(self, guild_id: int, days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        return await self._repo.get_top_channels(guild_id, days, limit)

    async def get_activity_by_hour(self, guild_id: int, days: int = 7) -> List[Dict[str, int]]:
        raw = await self._repo.get_activity_by_hour(guild_id, days)
        result = {str(h).zfill(2): 0 for h in range(24)}
        for row in raw:
            hour = str(row["hour"]).zfill(2)
            result[hour] = row["count"]
        return [{"hour": h, "count": c} for h, c in result.items()]

    async def get_leaderboard(self, guild_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._repo.get_leaderboard(guild_id, days, limit)
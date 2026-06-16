from typing import Optional
from disnake.ext import commands
from application.services import StatsService
from infrastructure.logging import get_logger
from presentation.cogs import StatsCog

logger = get_logger(__name__)

class StatsModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[StatsCog] = None

    async def get_stats_service(self) -> StatsService:
        return await self._container.get_stats_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[StatsCog]:
        if self._cog:
            return self._cog
        try:
            service = await self.get_stats_service()
            self._cog = StatsCog(bot, service)
            logger.info("StatsCog created and configured")
            return self._cog
        except Exception as e:
            logger.error("Failed to create StatsCog: %s", e)
            return None

    async def shutdown(self):
        self._cog = None
        logger.info("StatsModule shutdown")
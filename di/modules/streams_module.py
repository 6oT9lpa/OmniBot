from typing import Optional

from disnake.ext import commands

from application.services import CreatorAlertService
from infrastructure.logging import get_logger
from presentation.cogs import StreamsCog

logger = get_logger(__name__)


class StreamsModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[StreamsCog] = None

    async def get_creator_alert_service(self) -> CreatorAlertService:
        return await self._container.get_creator_alert_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[StreamsCog]:
        if self._cog:
            return self._cog
        try:
            service = await self.get_creator_alert_service()
            self._cog = StreamsCog(bot, service)
            logger.info("StreamsCog created and configured")
            return self._cog
        except Exception as exc:
            logger.error("Failed to create StreamsCog: %s", exc)
            return None

    async def shutdown(self):
        self._cog = None
        logger.info("StreamsModule shutdown")

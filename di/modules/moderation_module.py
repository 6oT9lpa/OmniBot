from typing import Optional

from disnake.ext import commands

from application.services import ModerationHistoryService, ModeratorService, LoggingService
from infrastructure.logging import get_logger
from presentation.cogs import ModerationCog

logger = get_logger(__name__)


class ModerationModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[ModerationCog] = None

    async def get_moderator_service(self) -> ModeratorService:
        return await self._container.get_moderator_service()

    async def get_history_service(self) -> ModerationHistoryService:
        return await self._container.get_moderation_history_service()
    
    async def get_logging_service(self) -> LoggingService:
        return await self._container.get_logging_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[ModerationCog]:
        if self._cog:
            return self._cog

        try:
            moderator_service = await self.get_moderator_service()
            history_service = await self.get_history_service()
            logging_service = await self.get_logging_service()
            self._cog = ModerationCog(moderator_service, history_service, logging_service)
            logger.info("ModerationCog created and configured")
            return self._cog
        except Exception as exc:
            logger.error("Failed to create ModerationCog: %s", exc)
            return None

    async def shutdown(self):
        self._cog = None
        logger.info("ModerationModule shutdown")
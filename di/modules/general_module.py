from typing import Optional

from disnake.ext import commands

from infrastructure.logging import get_logger
from presentation.cogs import GeneralCog

logger = get_logger(__name__)


class GeneralModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[GeneralCog] = None

    async def get_cog(self, bot: commands.Bot) -> Optional[GeneralCog]:
        if self._cog:
            return self._cog

        try:
            self._cog = GeneralCog(bot)
            logger.info("GeneralCog created and configured")
            return self._cog
        except Exception as exc:
            logger.error("Failed to create GeneralCog: %s", exc)
            return None

    async def shutdown(self):
        self._cog = None
        logger.info("GeneralModule shutdown")

from typing import Optional

from disnake.ext import commands

from infrastructure.logging import get_logger
from presentation.cogs.labeling_cog import LabelingCog

logger = get_logger(__name__)


class LabelingModule:
    def __init__(self, container) -> None:
        self._container = container
        self._cog: Optional[LabelingCog] = None

    async def get_cog(self, bot: commands.Bot) -> LabelingCog:
        if self._cog is None:
            self._cog = LabelingCog(
                bot,
                await self._container.get_moderation_labeling_service(),
                self._container.config.discord_owner_id,
            )
            logger.info("LabelingCog configured")
        return self._cog

    async def shutdown(self) -> None:
        self._cog = None

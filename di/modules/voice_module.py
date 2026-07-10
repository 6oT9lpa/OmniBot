from typing import Optional
from disnake.ext import commands
from application.services import VoiceService
from infrastructure.logging import get_logger
from presentation.cogs import VoiceCog

logger = get_logger(__name__)

class VoiceModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[VoiceCog] = None

    async def get_voice_service(self) -> VoiceService:
        return await self._container.get_voice_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[VoiceCog]:
        if self._cog:
            return self._cog
        try:
            service = await self.get_voice_service()
            self._cog = VoiceCog(bot, service)
            logger.info("VoiceCog created and configured")
            return self._cog
        except Exception as e:
            logger.error("Failed to create VoiceCog: %s", e)
            return None

    async def shutdown(self):
        service = getattr(self._container, "_voice_service", None)
        if service is not None:
            await service.shutdown()
        self._cog = None
        logger.info("VoiceModule shutdown")

from typing import Optional

from disnake.ext import commands

from application.services import WelcomeService, ChannelService
from infrastructure.logging import get_logger
from presentation.cogs import MemberEventsCog
from presentation.cogs.member_events import WelcomeConfigCommands

logger = get_logger(__name__)


class MemberEventsModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[MemberEventsCog] = None
        self._welcome_commands_cog: Optional[WelcomeConfigCommands] = None

    async def get_channel_service(self) -> ChannelService:
        return await self._container.get_channel_service()

    async def get_welcome_service(self) -> WelcomeService:
        return await self._container.get_welcome_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[MemberEventsCog]:
        if self._cog:
            return self._cog

        try:
            channel_service = await self.get_channel_service()
            welcome_service = await self.get_welcome_service()

            self._cog = MemberEventsCog(
                bot=bot,
                channel_service=channel_service,
                welcome_service=welcome_service,
            )
            
            logger.info("MemberEventsCog created and configured")
            return self._cog
            
        except Exception as e:
            logger.error(f"Failed to create MemberEventsCog: {e}")
            return None

    async def get_welcome_commands_cog(self, bot: commands.Bot) -> Optional[WelcomeConfigCommands]:
        if self._welcome_commands_cog:
            return self._welcome_commands_cog

        try:
            welcome_service = await self.get_welcome_service()

            self._welcome_commands_cog = WelcomeConfigCommands(
                bot=bot,
                welcome_service=welcome_service,
            )
            
            logger.info("WelcomeConfigCommands created and configured")
            return self._welcome_commands_cog
            
        except Exception as e:
            logger.error(f"Failed to create WelcomeConfigCommands: {e}")
            return None

    async def shutdown(self):
        self._cog = None
        self._welcome_commands_cog = None
        logger.info("MemberEventsModule shutdown")
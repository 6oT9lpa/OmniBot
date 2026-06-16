import asyncio
import signal
import sys

from di import Container
from presentation import DiscordBot
from infrastructure.logging import get_logger 
from presentation.cogs.roles_cog import RolesCog
from presentation.cogs.stats_cog import StatsCog
from presentation.cogs.voice_cog import VoiceCog

logger = get_logger(__name__)


class Bootstrap:
    def __init__(self):
        self.container = Container()
        self.bot: DiscordBot = None
        self._role_service = None
        self._stats_service = None
        self._voice_service = None

    async def run(self):
        try:
            self._role_service = await self.container.get_role_service()
            self._stats_service = await self.container.get_stats_service()
            self._voice_service = await self.container.get_voice_service()
            audit_log_service = await self.container.get_audit_log_service()
            logging_service = await self.container.get_logging_service()
            moderator_service = await self.container.get_moderator_service()

            if self._role_service is None:
                logger.error("Failed to get role service from container!")
                return
            
            logger.info(f"Role service obtained: {self._role_service}")
            
            self.bot = DiscordBot(
                config=self.container.config,
                role_service=self._role_service
            )
            audit_log_service.set_bot(self.bot)
            logging_service.set_bot(self.bot)
            moderator_service.set_bot(self.bot)
            
            await self._register_commands()
            await self._register_member_events_cog()
            await self._register_logging_cog()
            await self._register_moderation_cog()
            
            self._setup_signal_handlers()
            
            token = self.container.config.discord_token.get_secret_value()
            logger.info("Starting bot...")
            await self.bot.start(token)
            
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Shutting down...")
            await self._shutdown()
        except asyncio.CancelledError:
            logger.info("Task cancelled. Shutting down...")
            await self._shutdown()
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self._shutdown()
            sys.exit(1)
    
    def _setup_signal_handlers(self):
        try:
            loop = asyncio.get_event_loop()
            
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(
                        sig,
                        lambda s=sig: asyncio.create_task(self._shutdown())
                    )
                except (NotImplementedError, ValueError):
                    pass
        except Exception as e:
            logger.warning(f"Could not setup signal handlers: {e}")
    
    async def _register_commands(self):
        logger.info("Registering commands...")
        
        self.bot.add_cog(RolesCog(self.bot, self._role_service))
        logger.info("RolesCog registered")

        self.bot.add_cog(StatsCog(self.bot, self._stats_service))
        logger.info("StatsCog registered")

        self.bot.add_cog(VoiceCog(self.bot, self._voice_service))
        logger.info("VoiceCog registered")

        logger.info("All cogs registered successfully")
    
    async def _register_member_events_cog(self):
        logger.info("Registering member events cog...")
        
        member_events_module = self.container.get_member_events_module()
        
        cog = await member_events_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("MemberEventsCog registered")
        else:
            logger.warning("Failed to register MemberEventsCog")
        
        welcome_commands = await member_events_module.get_welcome_commands_cog(self.bot)
        if welcome_commands:
            self.bot.add_cog(welcome_commands)
            logger.info("WelcomeConfigCommands registered")
        else:
            logger.warning("Failed to register WelcomeConfigCommands")

    async def _register_logging_cog(self):
        logger.info("Registering logging cog...")
        logging_module = self.container.get_logging_module()
        cog = await logging_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("LoggingCog registered")
        else:
            logger.warning("Failed to register LoggingCog")

    async def _register_moderation_cog(self):
        logger.info("Registering moderation cog...")
        moderation_module = self.container.get_moderation_module()
        cog = await moderation_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("ModerationCog registered")
        else:
            logger.warning("Failed to register ModerationCog")
        
    async def _shutdown(self):
        logger.info("Shutting down...")
        
        if self.bot and not self.bot.is_closed():
            try:
                await self.bot.close()
                logger.info("Bot closed")
            except Exception as e:
                logger.error(f"Error closing bot: {e}")
        
        if self.container:
            try:
                await self.container.shutdown()
                logger.info("Container shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down container: {e}")
        
        logger.info("Shutdown complete")


def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Unhandled exception: {msg}")
    loop.stop()
import asyncio
import signal
import sys

from di import Container
from presentation import DiscordBot
from infrastructure.logging import get_logger

from di.modules import (
    GeneralModule,
    LoggingModule,
    MemberEventsModule,
    ModerationModule,
    RolesModule,
    StatsModule,
    VoiceModule,
    StreamsModule,
    AiModerationModule,
    LabelingModule,
)

logger = get_logger(__name__)


class Bootstrap:
    def __init__(self):
        self.container = Container()
        self.bot: DiscordBot = None
        self._role_service = None
        self._stats_service = None
        self._voice_service = None

        # Модули для когов
        self._general_module = None
        self._roles_module = None
        self._stats_module = None
        self._voice_module = None
        self._logging_module = None
        self._moderation_module = None
        self._member_events_module = None
        self._streams_module = None
        self._ai_moderation_module = None
        self._labeling_module = None
        self._shutdown_lock = asyncio.Lock()
        self._shutdown_complete = False

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

            # Инициализация модулей
            self._general_module = GeneralModule(self.container)
            self._roles_module = RolesModule(self.container)
            self._stats_module = StatsModule(self.container)
            self._voice_module = VoiceModule(self.container)
            self._logging_module = LoggingModule(self.container)
            self._moderation_module = ModerationModule(self.container)
            self._member_events_module = MemberEventsModule(self.container)
            self._streams_module = StreamsModule(self.container)
            self._ai_moderation_module = AiModerationModule(self.container)
            self._labeling_module = LabelingModule(self.container)

            # Регистрация всех когов через модули
            await self._register_general_cog()
            await self._register_roles_cog()
            await self._register_stats_cog()
            await self._register_voice_cog()
            await self._register_member_events_cog()
            await self._register_logging_cog()
            await self._register_moderation_cog()
            await self._register_streams_cog()
            await self._register_ai_moderation_cog()
            await self._register_labeling_cog()

            self._setup_signal_handlers()

            token = self.container.config.discord_token.get_secret_value()
            logger.info("Starting bot...")
            await self.bot.start(token)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Shutting down...")
        except asyncio.CancelledError:
            logger.info("Task cancelled. Shutting down...")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            await self._shutdown()

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

    # ---------- Регистрация когов через модули ----------
    async def _register_general_cog(self):
        logger.info("Registering GeneralCog via GeneralModule...")
        cog = await self._general_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("GeneralCog registered")
        else:
            logger.warning("Failed to register GeneralCog")

    async def _register_roles_cog(self):
        logger.info("Registering RolesCog via RolesModule...")
        cog = await self._roles_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("RolesCog registered")
        else:
            logger.warning("Failed to register RolesCog")

    async def _register_stats_cog(self):
        logger.info("Registering StatsCog via StatsModule...")
        cog = await self._stats_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("StatsCog registered")
        else:
            logger.warning("Failed to register StatsCog")

    async def _register_voice_cog(self):
        logger.info("Registering VoiceCog via VoiceModule...")
        cog = await self._voice_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("VoiceCog registered")
        else:
            logger.warning("Failed to register VoiceCog")

    async def _register_member_events_cog(self):
        logger.info("Registering member events cog...")
        cog = await self._member_events_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("MemberEventsCog registered")
        else:
            logger.warning("Failed to register MemberEventsCog")

        welcome_commands = await self._member_events_module.get_welcome_commands_cog(self.bot)
        if welcome_commands:
            self.bot.add_cog(welcome_commands)
            logger.info("WelcomeConfigCommands registered")
        else:
            logger.warning("Failed to register WelcomeConfigCommands")

    async def _register_logging_cog(self):
        logger.info("Registering logging cog...")
        cog = await self._logging_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("LoggingCog registered")
        else:
            logger.warning("Failed to register LoggingCog")

    async def _register_moderation_cog(self):
        logger.info("Registering moderation cog...")
        cog = await self._moderation_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("ModerationCog registered")
        else:
            logger.warning("Failed to register ModerationCog")

    async def _register_streams_cog(self):
        logger.info("Registering streams cog...")
        cog = await self._streams_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("StreamsCog registered")
        else:
            logger.warning("Failed to register StreamsCog")

    async def _register_ai_moderation_cog(self):
        cog = await self._ai_moderation_module.get_cog(self.bot)
        if cog:
            self.bot.add_cog(cog)
            logger.info("AiModerationCog registered")
        else:
            logger.warning("AI moderation cog is not configured")

    async def _register_labeling_cog(self):
        cog = await self._labeling_module.get_cog(self.bot)
        self.bot.add_cog(cog)
        logger.info("LabelingCog registered")

    # ---------- Завершение работы ----------
    async def _shutdown(self):
        async with self._shutdown_lock:
            if self._shutdown_complete:
                return
            logger.info("Shutting down...")

            if self._general_module:
                await self._general_module.shutdown()
            if self._roles_module:
                await self._roles_module.shutdown()
            if self._stats_module:
                await self._stats_module.shutdown()
            if self._voice_module:
                await self._voice_module.shutdown()
            if self._logging_module:
                await self._logging_module.shutdown()
            if self._moderation_module:
                await self._moderation_module.shutdown()
            if self._member_events_module:
                await self._member_events_module.shutdown()
            if self._streams_module:
                await self._streams_module.shutdown()
            if self._ai_moderation_module:
                await self._ai_moderation_module.shutdown()
            if self._labeling_module:
                await self._labeling_module.shutdown()

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

            self._shutdown_complete = True
            logger.info("Shutdown complete")


def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Unhandled exception: {msg}")
    loop.stop()

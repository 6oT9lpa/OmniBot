import asyncio
import disnake
from disnake.ext import commands

from infrastructure.config import BotConfig
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DiscordBot(commands.Bot):
    def __init__(
        self,
        config: BotConfig,
        role_service=None
    ):
        self._config = config
        self._role_service = role_service

        intents = disnake.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        super().__init__(
            command_prefix=self._config.command_prefix,
            intents=intents,
            activity=disnake.Game(name=self._config.activity_name),
            status=disnake.Status.online,
            test_guilds=[self._config.discord_guild_id],
        )

        self._ready = asyncio.Event()

        if self._role_service:
            self._role_service.set_bot(self)  

    async def on_ready(self):
        if not self._ready.is_set():
            self._ready.set()
            
            logger.info("=" * 50)
            logger.info(f"Bot: {self.user.name}")
            logger.info(f"ID: {self.user.id}")
            
            if self.guilds:
                guild = self.guilds[0]
                logger.info(f"Guild: {guild.name}")
                logger.info(f"Members: {guild.member_count}")
            
            logger.info("=" * 50)
            
            # Синхронизируем роли при старте
            if self.guilds and self._role_service:
                try:
                    await self._role_service.sync_roles(self.guilds[0])
                except Exception as e:
                    logger.error(f"Failed to sync roles: {e}")

    async def on_application_command_error(self, interaction: disnake.Interaction, error: Exception):
        logger.error("Application command error command=%s error=%s", getattr(interaction, "command", None), error, exc_info=True)
        if interaction.response.is_done():
            return
        embed = disnake.Embed(
            title="Ошибка команды",
            description=str(error),
            color=disnake.Color.red(),
        )
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            logger.exception("Failed to send application command error response")

    async def on_interaction_error(self, interaction: disnake.Interaction, error: Exception):
        logger.error("Interaction error custom_id=%s error=%s", getattr(interaction, "custom_id", None), error, exc_info=True)
        if interaction.response.is_done():
            return
        try:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    title="Ошибка взаимодействия",
                    description=str(error),
                    color=disnake.Color.red(),
                ),
                ephemeral=True,
            )
        except Exception:
            logger.exception("Failed to send interaction error response")

    async def close(self):
        """Закрытие бота"""
        logger.info("Closing bot...")
        await super().close()
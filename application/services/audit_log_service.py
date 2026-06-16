from typing import Optional

import disnake

from core.domain.channel_purpose import ChannelPurpose
from core.interfaces.services import AuditLogServiceInterface, ChannelServiceInterface
from infrastructure.config import BotConfig
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class AuditLogService(AuditLogServiceInterface):
    def __init__(
        self,
        config: BotConfig,
        channel_service: ChannelServiceInterface,
    ):
        self._config = config
        self._channel_service = channel_service
        self._bot: Optional[disnake.Client] = None

    def set_bot(self, bot: disnake.Client) -> None:
        self._bot = bot

    async def send_to_log_channel(
        self,
        guild_id: int,
        embed: disnake.Embed,
        *,
        channel_id: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> None:
        channel = await self.get_log_channel(
            guild_id,
            event_type=event_type,
            channel_id=channel_id,
        )

        if not channel:
            logger.debug("No log channel for guild id=%s", guild_id)
            return
        
        try:
            await channel.send(embed=embed)
        except Exception as exc:
            logger.error("Failed to send audit log to guild id=%s: %s", guild_id, exc)

    async def get_log_channel(
        self,
        guild_id: int,
        event_type: Optional[str] = None,
        channel_id: Optional[int] = None,
    ) -> Optional[disnake.TextChannel]:
        if not self._bot:
            return None
        guild = self._bot.get_guild(guild_id)
        if not guild:
            return None

        if channel_id is not None:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, disnake.TextChannel):
                return channel

        if event_type:
            purpose = self._event_type_to_purpose(event_type)
            if purpose:
                purpose_channel_id = await self._channel_service.get_purpose_channel(guild_id, purpose)
                if purpose_channel_id is not None:
                    channel = guild.get_channel(purpose_channel_id)
                    if isinstance(channel, disnake.TextChannel):
                        return channel

        return None

    @staticmethod
    def _event_type_to_purpose(event_type: Optional[str]) -> Optional[ChannelPurpose]:
        if not event_type:
            return None
        if event_type.startswith("message"):
            return ChannelPurpose.MESSAGE_LOG
        if event_type.startswith("voice"):
            return ChannelPurpose.CHANNEL_LOG
        if event_type.startswith("channel"):
            return ChannelPurpose.CHANNEL_LOG 
        if event_type.startswith("moderation"):
            return ChannelPurpose.MOD_LOG
        
        return ChannelPurpose.MOD_LOG

    async def setup_log_channels(
        self,
        guild: disnake.Guild,
        logs_channel_id: int,
        deleted_messages_channel_id: Optional[int] = None,
    ) -> bool:
        channel = guild.get_channel(logs_channel_id)
        if not isinstance(channel, disnake.TextChannel):
            return False

        self._config.log_channel_id = logs_channel_id
        logger.info("Configured log channel id=%s for guild id=%s", logs_channel_id, guild.id)

        if deleted_messages_channel_id is not None:
            deleted_channel = guild.get_channel(deleted_messages_channel_id)
            if not isinstance(deleted_channel, disnake.TextChannel):
                return False

            self._config.deleted_messages_channel_id = deleted_messages_channel_id
            logger.info(
                "Configured deleted-message log channel id=%s for guild id=%s",
                deleted_messages_channel_id,
                guild.id,
            )

        return True
from typing import Optional, Dict, Any, List

import disnake

from core.domain.channel_purpose import ChannelPurpose
from core.interfaces.repositories import ChannelConfigRepositoryInterface
from core.interfaces.services import ChannelServiceInterface
from infrastructure.config import BotConfig
from infrastructure.database.repositories.channel_config_repository import ChannelConfigRepository
from infrastructure.logging import get_logger
from infrastructure.database import DatabaseManager

logger = get_logger(__name__)


class ChannelService(ChannelServiceInterface):
    def __init__(self, channel_config_repo: ChannelConfigRepositoryInterface):
        self._channel_config_repo = channel_config_repo

    async def get_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        return await self._channel_config_repo.get_by_channel(channel_id)

    async def get_by_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        return await self._channel_config_repo.get_by_guild(guild_id)

    async def upsert_channel(
        self,
        channel_id: int,
        guild_id: int,
        *,
        is_ai_whitelisted: bool = False,
        welcome_enabled: bool = True,
        slowmode_override: Optional[int] = None,
        auto_delete_after: Optional[int] = None,
        custom_name: Optional[str] = None,
    ) -> None:
        await self._channel_config_repo.upsert_channel(
            channel_id, guild_id,
            is_ai_whitelisted=is_ai_whitelisted,
            welcome_enabled=welcome_enabled,
            slowmode_override=slowmode_override,
            auto_delete_after=auto_delete_after,
            custom_name=custom_name,
        )
        logger.debug("Upserted channel_config for channel %s", channel_id)

    async def set_purpose(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
        channel_id: int,
    ) -> None:
        await self._channel_config_repo.set_purpose(guild_id, purpose, channel_id)
        logger.info("Set channel purpose '%s' -> channel %s", purpose.value, channel_id)

    async def remove_purpose(self, guild_id: int, purpose: ChannelPurpose) -> bool:
        return await self._channel_config_repo.remove_purpose(guild_id, purpose)

    async def get_purpose_channel(self, guild_id: int, purpose: ChannelPurpose) -> Optional[int]:
        return await self._channel_config_repo.get_purpose_channel(guild_id, purpose)

    async def get_all_purposes(self, guild_id: int) -> Dict[str, int]:
        return await self._channel_config_repo.get_all_purposes(guild_id)

    async def get_log_channel(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
    ) -> Optional[disnake.abc.GuildChannel]:
        channel_id = await self.get_purpose_channel(guild_id, purpose)
        if not channel_id:
            return None
        return channel_id
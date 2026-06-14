from typing import Optional, Dict, Any, List

from core.domain.channel_purpose import ChannelPurpose
from core.interfaces.repositories import ChannelConfigRepositoryInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ChannelService:
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
        logger.debug(f"Upserted channel_config for channel {channel_id}")

    async def set_purpose(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
        channel_id: int,
    ) -> None:
        await self._channel_config_repo.set_purpose(guild_id, purpose, channel_id)
        logger.info(f"Set channel purpose '{purpose.value}' -> channel {channel_id}")

    async def remove_purpose(self, guild_id: int, purpose: ChannelPurpose) -> bool:
        return await self._channel_config_repo.remove_purpose(guild_id, purpose)

    async def get_purpose_channel(self, guild_id: int, purpose: ChannelPurpose) -> Optional[int]:
        return await self._channel_config_repo.get_purpose_channel(guild_id, purpose)

    async def get_all_purposes(self, guild_id: int) -> Dict[str, int]:
        return await self._channel_config_repo.get_all_purposes(guild_id)
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from core.domain.channel_purpose import ChannelPurpose


class ChannelServiceInterface(ABC):
    @abstractmethod
    async def get_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_by_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def set_purpose(
        self,
        guild_id: int,
        purpose: ChannelPurpose,
        channel_id: int,
    ) -> None:
        pass

    @abstractmethod
    async def remove_purpose(self, guild_id: int, purpose: ChannelPurpose) -> bool:
        pass

    @abstractmethod
    async def get_purpose_channel(self, guild_id: int, purpose: ChannelPurpose) -> Optional[int]:
        pass

    @abstractmethod
    async def get_all_purposes(self, guild_id: int) -> Dict[str, int]:
        pass

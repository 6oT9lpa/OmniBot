from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ChannelConfigRepositoryInterface(ABC):
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

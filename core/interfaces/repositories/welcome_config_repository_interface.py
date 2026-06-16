from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class WelcomeConfigRepositoryInterface(ABC):
    @abstractmethod
    async def get_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def create_or_update(
        self,
        guild_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        color: Optional[int] = None,
        is_enabled: Optional[bool] = None,
        rules_channel_id: Optional[int] = None,
        roles_channel_id: Optional[int] = None,
    ) -> bool:
        pass

    @abstractmethod
    async def set_enabled(self, guild_id: int, is_enabled: bool) -> bool:
        pass

    @abstractmethod
    async def delete_config(self, guild_id: int) -> bool:
        pass

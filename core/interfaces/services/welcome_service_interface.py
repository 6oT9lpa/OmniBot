from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import disnake


class WelcomeServiceInterface(ABC):
    @abstractmethod
    async def get_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_config(
        self,
        guild_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        color: Optional[int] = None,
        rules_channel_id: Optional[int] = None,
        roles_channel_id: Optional[int] = None,
    ) -> bool:
        pass

    @abstractmethod
    async def set_enabled(self, guild_id: int, is_enabled: bool) -> bool:
        pass

    @abstractmethod
    async def reset_config(self, guild_id: int) -> bool:
        pass

    @abstractmethod
    def format_description(
        self,
        description: str,
        member: disnake.Member,
        guild: disnake.Guild,
        rules_channel_id: Optional[int] = None,
        roles_channel_id: Optional[int] = None,
        mention_style: str = "mentions",
    ) -> str:
        pass

    @abstractmethod
    def build_embed(
        self,
        member: disnake.Member,
        config: Optional[Dict[str, Any]] = None,
    ) -> disnake.Embed:
        pass

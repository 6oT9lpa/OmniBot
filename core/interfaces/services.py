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
    ) -> str:
        pass

    @abstractmethod
    def build_embed(
        self,
        member: disnake.Member,
        config: Optional[Dict[str, Any]] = None,
    ) -> disnake.Embed:
        pass


class RoleServiceInterface(ABC):
    @abstractmethod
    async def assign_auto_roles(self, member: disnake.Member) -> List[disnake.Role]:
        pass

    @abstractmethod
    async def sync_roles(self, guild: disnake.Guild) -> int:
        pass

    @abstractmethod
    async def get_all_roles(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_public_roles(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def set_auto_assign(self, role_id: int, is_auto_assign: bool) -> None:
        pass

    @abstractmethod
    async def set_role_public(self, role_id: int, is_public: bool) -> bool:
        pass
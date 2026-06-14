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


class RoleRepositoryInterface(ABC):
    @abstractmethod
    async def add_role(
        self,
        role_id: int,
        name: str,
        color: Optional[int] = None,
        position: Optional[int] = None,
        is_auto_assign: bool = False,
        is_public: bool = True,
        display_emoji: Optional[str] = None,
    ) -> bool:
        pass

    @abstractmethod
    async def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_auto_assign_roles(self) -> List[int]:
        pass

    @abstractmethod
    async def set_auto_assign(self, role_id: int, is_auto_assign: bool) -> None:
        pass

    @abstractmethod
    async def get_all_roles(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_public_roles(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def remove_role(self, role_id: int) -> bool:
        pass


class RolePanelMessageRepositoryInterface(ABC):
    @abstractmethod
    async def create(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        embed_title: str,
        embed_description: str,
        embed_color: int,
        created_by: int,
    ) -> int:
        pass

    @abstractmethod
    async def get_by_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_by_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_by_message(self, message_id: int) -> bool:
        pass


class RolePanelButtonRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        panel_message_id: int,
        role_id: int,
        role_name: str,
        emoji: Optional[str] = None,
        position: int = 0,
    ) -> int:
        pass

    @abstractmethod
    async def remove(self, panel_message_id: int, role_id: int) -> bool:
        pass

    @abstractmethod
    async def get_all(self, panel_message_id: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def clear_all(self, panel_message_id: int) -> int:
        pass
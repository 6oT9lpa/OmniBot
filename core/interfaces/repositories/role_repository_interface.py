from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
        guild_id: Optional[int] = None,
    ) -> bool:
        pass

    @abstractmethod
    async def get_role(self, role_id: int, guild_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_auto_assign_roles(self, guild_id: Optional[int] = None) -> List[int]:
        pass

    @abstractmethod
    async def set_auto_assign(self, role_id: int, is_auto_assign: bool, guild_id: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def set_public(self, role_id: int, is_public: bool, guild_id: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def get_all_roles(self, guild_id: Optional[int] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_public_roles(self, guild_id: Optional[int] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def sync_from_discord(self, guild_id: int, discord_roles: List[Dict[str, Any]]) -> int:
        pass

    @abstractmethod
    async def remove_role(self, role_id: int) -> bool:
        pass

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import disnake

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
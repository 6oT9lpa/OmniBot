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

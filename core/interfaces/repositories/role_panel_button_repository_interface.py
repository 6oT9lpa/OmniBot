from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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
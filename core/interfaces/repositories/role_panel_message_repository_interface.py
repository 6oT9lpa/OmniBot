from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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

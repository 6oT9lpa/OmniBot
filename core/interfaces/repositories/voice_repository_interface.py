from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from application.dto.voice_dto import VoiceRoomDTO


class VoiceRepositoryInterface(ABC):
    @abstractmethod
    async def create(self, dto: VoiceRoomDTO) -> None:
        """Создать запись о голосовой комнате"""
        pass

    @abstractmethod
    async def delete(self, channel_id: int) -> None:
        """Удалить запись о голосовой комнате"""
        pass

    @abstractmethod
    async def get(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Получить запись по ID канала"""
        pass

    @abstractmethod
    async def get_by_owner(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Получить комнату по владельцу"""
        pass

    @abstractmethod
    async def get_all(self, guild_id: int) -> List[Dict[str, Any]]:
        """Получить все комнаты гильдии"""
        pass

    @abstractmethod
    async def update_admin(self, channel_id: int, admin_id: Optional[int]) -> None:
        """Обновить владельца комнаты"""
        pass

    @abstractmethod
    async def update_owner(self, channel_id: int, owner_id: int) -> None:
        """Update dynamic voice room owner."""
        pass

    @abstractmethod
    async def claim_admin(self, channel_id: int, admin_id: int) -> bool:
        """Atomically claim an unoccupied temporary admin slot."""
        pass

    @abstractmethod
    async def clear_admin_if(self, channel_id: int, admin_id: int) -> bool:
        """Clear the admin slot only when it is held by the expected member."""
        pass

    @abstractmethod
    async def add_member(self, channel_id: int, guild_id: int, user_id: int) -> None:
        """Track a member currently connected to a dynamic voice room."""
        pass

    @abstractmethod
    async def remove_member(self, channel_id: int, user_id: int) -> None:
        """Stop tracking a member for a dynamic voice room."""
        pass

    @abstractmethod
    async def clear_members(self, channel_id: int) -> None:
        """Remove all tracked members for a dynamic voice room."""
        pass

    @abstractmethod
    async def get_member_ids(self, channel_id: int) -> List[int]:
        """Return tracked member ids for a dynamic voice room."""
        pass

    @abstractmethod
    async def set_persistent(self, channel_id: int, persistent: bool) -> None:
        """Установить флаг постоянства комнаты"""
        pass

    @abstractmethod
    async def set_config(self, key: str, value: str) -> None:
        """Сохранить конфигурацию"""
        pass

    @abstractmethod
    async def get_config(self, key: str) -> Optional[str]:
        """Получить конфигурацию"""
        pass

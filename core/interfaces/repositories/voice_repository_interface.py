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
    async def update_owner(self, channel_id: int, new_owner_id: int) -> None:
        """Обновить владельца комнаты"""
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
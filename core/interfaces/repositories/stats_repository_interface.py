from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class StatsRepositoryInterface(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: int, guild_id: int) -> None:
        """Создать запись пользователя, если не существует"""
        pass

    @abstractmethod
    async def increment_messages(self, user_id: int, guild_id: int) -> None:
        """Увеличить счётчик сообщений"""
        pass

    @abstractmethod
    async def add_voice_minutes(self, user_id: int, guild_id: int, minutes: int) -> None:
        """Добавить минуты голосовой активности"""
        pass

    @abstractmethod
    async def increment_warnings(self, user_id: int, guild_id: int) -> None:
        """Увеличить счётчик предупреждений"""
        pass

    @abstractmethod
    async def log_message_to_history(self, message_id: int, user_id: int, guild_id: int, channel_id: int) -> None:
        """Записать сообщение в историю"""
        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Получить статистику пользователя"""
        pass

    @abstractmethod
    async def get_server_stats(self, guild_id: int, period: int) -> Dict[str, Any]:
        """Получить общую статистику сервера"""
        pass

    @abstractmethod
    async def get_top_channels(self, guild_id: int, days: int, limit: int) -> List[Dict[str, Any]]:
        """Получить топ-каналов"""
        pass

    @abstractmethod
    async def get_activity_by_hour(self, guild_id: int, days: int) -> List[Dict[str, int]]:
        """Получить активность по часам"""
        pass

    @abstractmethod
    async def get_leaderboard(self, guild_id: int, days: int, limit: int) -> List[Dict[str, Any]]:
        """Получить топ-участников"""
        pass

    @abstractmethod
    async def reset_user_stats(self, user_id: int, guild_id: int) -> None:
        """Сбросить статистику пользователя"""
        pass

    @abstractmethod
    async def delete_user_stats(self, user_id: int, guild_id: int) -> None:
        """Удалить запись пользователя"""
        pass
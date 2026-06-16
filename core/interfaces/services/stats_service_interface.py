from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List

import disnake


class StatsServiceInterface(ABC):
    @abstractmethod
    async def log_message(self, message: disnake.Message) -> None:
        """Логирование сообщения"""
        pass

    @abstractmethod
    async def log_voice_activity(self, member: disnake.Member, joined_at: datetime) -> None:
        """Логирование голосовой активности"""
        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Получение статистики пользователя"""
        pass

    @abstractmethod
    async def get_server_stats(self, guild_id: int, period: int = 7) -> Dict[str, Any]:
        """Получение общей статистики сервера"""
        pass

    @abstractmethod
    async def get_top_channels(self, guild_id: int, days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение топ-каналов по активности"""
        pass

    @abstractmethod
    async def get_activity_by_hour(self, guild_id: int, days: int = 7) -> List[Dict[str, int]]:
        """Получение активности по часам"""
        pass

    @abstractmethod
    async def get_leaderboard(self, guild_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ-участников"""
        pass
    
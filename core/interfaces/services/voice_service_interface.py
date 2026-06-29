from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import disnake


class VoiceServiceInterface(ABC):
    @abstractmethod
    async def create(self, member: disnake.Member, trigger_channel: disnake.VoiceChannel) -> Optional[disnake.VoiceChannel]:
        """Создать голосовую комнату для участника"""
        pass

    @abstractmethod
    async def delete(self, channel: disnake.VoiceChannel) -> None:
        """Удалить голосовую комнату"""
        pass

    @abstractmethod
    async def schedule_delete(self, channel: disnake.VoiceChannel, delay: float = 30.0) -> None:
        """Запланировать удаление комнаты"""
        pass

    @abstractmethod
    async def cancel_delete(self, channel_id: int) -> None:
        """Отменить запланированное удаление"""
        pass

    @abstractmethod
    async def handle_admin_leave(self, channel: disnake.VoiceChannel, old_admin: disnake.Member) -> None:
        """Обработка ухода владельца комнаты"""
        pass

    @abstractmethod
    async def rename(self, channel: disnake.VoiceChannel, new_name: str, user: disnake.Member) -> None:
        """Переименовать комнату"""
        pass

    @abstractmethod
    async def set_limit(self, channel: disnake.VoiceChannel, limit: int, user: disnake.Member) -> None:
        """Установить лимит участников"""
        pass

    @abstractmethod
    async def lock(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        """Закрыть комнату (запретить вход @everyone)"""
        pass

    @abstractmethod
    async def unlock(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        """Открыть комнату"""
        pass

    @abstractmethod
    async def transfer(self, channel: disnake.VoiceChannel, new_owner: disnake.Member, user: disnake.Member) -> None:
        """Передать владение комнатой"""
        pass

    @abstractmethod
    async def claim_admin(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        """Claim free temporary admin rights."""
        pass

    @abstractmethod
    async def release_admin(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        """Release temporary admin rights."""
        pass

    @abstractmethod
    async def assign_admin(
        self,
        channel: disnake.VoiceChannel,
        new_admin: Optional[disnake.Member],
        user: disnake.Member,
    ) -> None:
        """Owner-only temporary admin assignment."""
        pass

    @abstractmethod
    async def invite(self, channel: disnake.VoiceChannel, target: disnake.Member, user: disnake.Member) -> None:
        """Пригласить участника в комнату"""
        pass

    @abstractmethod
    async def kick(self, channel: disnake.VoiceChannel, target: disnake.Member, user: disnake.Member) -> None:
        """Выгнать участника из комнаты"""
        pass

    @abstractmethod
    async def ban(self, channel: disnake.VoiceChannel, target: disnake.Member, user: disnake.Member) -> None:
        """Забанить участника в комнате"""
        pass

    @abstractmethod
    async def set_trigger(self, guild_id: int, channel_id: int) -> None:
        """Установить триггерный канал"""
        pass

    @abstractmethod
    async def get_trigger(self, guild_id: int) -> Optional[int]:
        """Получить триггерный канал"""
        pass

    @abstractmethod
    async def remove_trigger(self, guild_id: int) -> None:
        """Удалить триггерный канал"""
        pass

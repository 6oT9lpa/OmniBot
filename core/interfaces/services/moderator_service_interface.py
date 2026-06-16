from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union

import disnake

class ModeratorServiceInterface(ABC):
    @abstractmethod
    async def warn_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: disnake.Member,
        reason: str,
        *,
        send_dm: bool = True,
        log_channel_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Выдать предупреждение пользователю"""
        pass
    
    @abstractmethod
    async def mute_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: disnake.Member,
        duration: int,
        reason: str,
        *,
        send_dm: bool = True,
        use_timeout: bool = True,
    ) -> Dict[str, Any]:
        """Выдать мут с пользователя"""
        pass
    
    @abstractmethod
    async def unmute_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: disnake.Member,
        reason: str = "Досрочное снятие мута",
    ) -> bool:
        """Снять мут с пользователя"""
        pass
    
    @abstractmethod
    async def kick_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: disnake.Member,
        reason: str,
        *,
        send_dm: bool = True,
    ) -> bool:
        """Исключить пользователя с сервера"""
        pass
    
    @abstractmethod
    async def ban_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: Union[disnake.Member, disnake.User],
        reason: str,
        *,
        delete_message_days: int = 1,
        send_dm: bool = True,
    ) -> bool:
        """Забанить пользователя"""
        pass
    
    @abstractmethod
    async def unban_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        guild: disnake.Guild,
        user_id: int,
        reason: str = "Разбан",
    ) -> bool:
        """Разбанить пользователя по ID"""
        pass
    
    @abstractmethod
    async def timeout_user(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: disnake.Member,
        duration: int,
        reason: str,
    ) -> bool:
        """Выдать Discord timeout"""
        pass
    
    @abstractmethod
    async def remove_timeout(
        self,
        moderator: Union[disnake.Member, disnake.User],
        target: disnake.Member,
        reason: str = "Досрочное снятие таймаута",
    ) -> bool:
        """Снять Discord timeout"""
        pass
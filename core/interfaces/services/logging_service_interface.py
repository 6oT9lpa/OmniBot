from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union

import disnake

from core.domain.value_objects import EventType, PunishmentType


class LoggingServiceInterface(ABC):
    """Service for logging events"""
    
    @abstractmethod
    async def log_message(
        self,
        message: disnake.Message,
        *,
        ai_flagged: bool = False,
        ai_reason: Optional[str] = None,
    ) -> None:
        """Save message to log"""
        pass
    
    @abstractmethod
    async def log_message_edit(
        self,
        before: disnake.Message,
        after: disnake.Message,
    ) -> None:
        """Record message edit"""
        pass
    
    @abstractmethod
    async def log_message_delete(
        self,
        message: disnake.Message,
        *,
        deleted_by: Optional[disnake.Member] = None, 
    ) -> None:
        """Record message deletion"""
        pass
    
    @abstractmethod
    async def log_bulk_delete(
        self,
        messages: List[disnake.Message],
        channel: disnake.TextChannel,
        deleted_by: Optional[disnake.Member] = None,
    ) -> None:
        """Record bulk message deletion"""
        pass
    
    @abstractmethod
    async def log_channel_event(
        self,
        event_type: EventType,
        channel: Union[disnake.TextChannel, disnake.VoiceChannel],
        *,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record channel event"""
        pass
    
    @abstractmethod
    async def log_role_event(
        self,
        event_type: EventType,
        role: disnake.Role,
        *,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record role event"""
        pass
    
    @abstractmethod
    async def log_voice_event(
        self,
        member: disnake.Member,
        before: Optional[disnake.VoiceState],
        after: Optional[disnake.VoiceState],
    ) -> None:
        """Record voice channel event"""
        pass
    
    @abstractmethod
    async def log_moderation_action(
        self,
        action_type: PunishmentType,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        duration: Optional[int] = None,
        punishment_id: Optional[int] = None,
    ) -> None:
        """Record moderator action"""
        pass

    @abstractmethod
    async def log_audit_mute(
        self,
        target: disnake.Member,
        duration_seconds: int,
        reason: str,
    ) -> None:
        """Log mute from Discord audit log"""
        pass

    @abstractmethod
    async def log_audit_unmute(
        self,
        target: disnake.Member,
        duration_seconds: int,
        reason: str,
    ) -> None:
        """Log unmute from Discord audit log"""
        pass

    @abstractmethod
    async def log_audit_ban(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
    ) -> None:
        """Log ban from Discord audit log"""
        pass

    @abstractmethod
    async def log_audit_unban(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
    ) -> None:
        """Log unban from Discord audit log"""
        pass

    @abstractmethod
    async def log_audit_kick(
        self,
        target: disnake.Member,
        reason: str,
    ) -> None:
        """Log kick from Discord audit log"""
        pass
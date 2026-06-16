from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

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
        """Record bulk message deletion with styled embed"""
        pass

    @abstractmethod
    async def log_channel_create(
        self,
        channel: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log channel creation"""
        pass

    @abstractmethod
    async def log_channel_delete(
        self,
        channel: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log channel deletion"""
        pass

    @abstractmethod
    async def log_channel_update(
        self,
        before: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        after: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log channel update with detailed changes"""
        pass
    
    @abstractmethod
    async def log_role_create(
        self,
        role: disnake.Role,
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log role creation with details"""
        pass

    @abstractmethod
    async def log_role_delete(
        self,
        role: disnake.Role,
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log role deletion"""
        pass

    @abstractmethod
    async def log_role_update(
        self,
        before: disnake.Role,
        after: disnake.Role,
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log role update with detailed changes (name, color, permissions, etc.)"""
        pass

    @abstractmethod
    async def log_member_role_update(
        self,
        member: disnake.Member,
        before_roles: List[disnake.Role],
        after_roles: List[disnake.Role],
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Log role changes for a member (added/removed roles)"""
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
        target: Union[disnake.Member, disnake.User],
        reason: str,
        *,
        guild_id: Optional[int] = None,
    ) -> None:
        """Log ban from Discord audit log"""
        pass

    @abstractmethod
    async def log_audit_unban(
        self,
        moderator: disnake.Member,
        target: Union[disnake.Member, disnake.User],
        reason: str,
        *,
        guild_id: Optional[int] = None,
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

    @abstractmethod
    async def cleanup_expired(self) -> None:
        """Cleanup expired log entries"""
        pass
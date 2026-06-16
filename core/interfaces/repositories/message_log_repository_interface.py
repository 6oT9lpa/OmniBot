from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class MessageLogRepositoryInterface(ABC):
    """Repository for message logging"""
    
    @abstractmethod
    async def add(
        self,
        dto: Any,
    ) -> int:
        """Add message log entry"""
        pass

    @abstractmethod
    async def cleanup_expired(
        self,
        cutoff_iso: str,
    ) -> int:
        """Cleanup expired entries"""
        pass

    @abstractmethod
    async def save_message(
        self,
        message_id: int,
        channel_id: int,
        guild_id: int,
        author_id: int,
        content: str,
        *,
        is_edited: bool = False,
        is_deleted: bool = False,
        edited_at: Optional[datetime] = None,
        ai_flagged: bool = False,
        ai_reason: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> None:
        """Save or update message in log"""
        pass
    
    @abstractmethod
    async def mark_as_deleted(
        self,
        message_id: int,
        deleted_at: Optional[datetime] = None,
    ) -> bool:
        """Mark message as deleted"""
        pass
    
    @abstractmethod
    async def mark_as_edited(
        self,
        message_id: int,
        new_content: str,
        edited_at: datetime,
    ) -> bool:
        """Update content of edited message"""
        pass
    
    @abstractmethod
    async def get_message_history(
        self,
        channel_id: int,
        limit: int = 100,
        *,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        author_id: Optional[int] = None,
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get message history with filters"""
        pass
    
    @abstractmethod
    async def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        pass
    
    @abstractmethod
    async def get_user_messages_count(
        self,
        user_id: int,
        guild_id: int,
        *,
        since: Optional[datetime] = None,
    ) -> int:
        """Get user message count"""
        pass
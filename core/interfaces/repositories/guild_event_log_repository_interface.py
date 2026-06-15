from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.domain.value_objects import EventType


class GuildEventLogRepositoryInterface(ABC):
    """Repository for server events"""
    
    @abstractmethod
    async def add(
        self,
        dto: Any,
    ) -> int:
        """Add event log entry"""
        pass

    @abstractmethod
    async def cleanup_expired(
        self,
        cutoff_iso: str,
    ) -> int:
        """Cleanup expired entries"""
        pass

    @abstractmethod
    async def log_event(
        self,
        guild_id: int,
        event_type: EventType,
        data: Dict[str, Any],
        *,
        user_id: Optional[int] = None,
        target_id: Optional[int] = None,
    ) -> int:
        """Log event to database"""
        pass
    
    @abstractmethod
    async def get_events(
        self,
        guild_id: int,
        event_type: Optional[EventType] = None,
        *,
        limit: int = 100,
        since: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get events with filters"""
        pass
    
    @abstractmethod
    async def get_member_join_leave_stats(
        self,
        guild_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get join/leave statistics"""
        pass
    
    @abstractmethod
    async def get_role_change_history(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get role change history for user"""
        pass
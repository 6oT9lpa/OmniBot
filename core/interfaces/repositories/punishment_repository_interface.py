from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.domain.value_objects import PunishmentType


class PunishmentRepositoryInterface(ABC):    
    @abstractmethod
    async def add(
        self,
        dto: Any,
    ) -> int:
        """Add new punishment"""
        pass

    @abstractmethod
    async def get(
        self,
        punishment_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get punishment by ID"""
        pass
    
    @abstractmethod
    async def get_active(
        self,
        guild_id: int,
        user_id: int,
        punishment_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Get active punishment"""
        pass
    
    @abstractmethod
    async def add_punishment(
        self,
        user_id: int,
        moderator_id: int,
        punishment_type: PunishmentType,
        reason: str,
        *,
        duration: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        message_id: Optional[int] = None,
    ) -> int:
        """Add new punishment"""
        pass
    
    @abstractmethod
    async def get_active_punishments(
        self,
        user_id: int,
        punishment_type: Optional[PunishmentType] = None,
    ) -> List[Dict[str, Any]]:
        """Get active punishments for user"""
        pass
    
    @abstractmethod
    async def get_punishment_history(
        self,
        user_id: int,
        limit: int = 50,
        *,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get punishment history for user"""
        pass
    
    @abstractmethod
    async def expire_punishment(self, punishment_id: int) -> bool:
        """Mark punishment as expired"""
        pass
    
    @abstractmethod
    async def revoke_punishment(
        self,
        punishment_id: int,
        revoked_by: int,
    ) -> bool:
        """Revoke punishment early"""
        pass
    
    @abstractmethod
    async def get_expired_punishments(self) -> List[Dict[str, Any]]:
        """Get all expired punishments for auto-removal"""
        pass
    
    @abstractmethod
    async def get_warning_count(
        self,
        user_id: int,
        *,
        since: Optional[datetime] = None,
    ) -> int:
        """Get warning count for user"""
        pass
    
    @abstractmethod
    async def get_all_active_mutes(self) -> List[Dict[str, Any]]:
        """Get all active mutes for verification"""
        pass

    @abstractmethod
    async def list_active(
        self,
        guild_id: int,
        punishment_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List active punishments"""
        pass

    @abstractmethod
    async def list_for_user(
        self,
        guild_id: int,
        user_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List punishments for user"""
        pass

    @abstractmethod
    async def deactivate(
        self,
        punishment_id: int,
    ) -> bool:
        """Deactivate punishment"""
        pass

    @abstractmethod
    async def cleanup_expired(
        self,
        cutoff_iso: str,
    ) -> int:
        """Cleanup expired entries"""
        pass
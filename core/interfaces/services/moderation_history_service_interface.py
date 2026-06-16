from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

import disnake

from core.domain.value_objects import PunishmentType


class ModerationHistoryServiceInterface(ABC):
    @abstractmethod
    async def list_active_punishments(
        self,
        guild_id: int,
        punishment_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get active punishments"""
        pass
    
    @abstractmethod
    async def get_user_history(
        self,
        user_id: int,
        guild_id: int,
        *,
        limit: int = 50,
        include_active: bool = True,
        include_expired: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get full punishment history for user"""
        pass
    
    @abstractmethod
    async def get_user_punishment_summary(
        self,
        user_id: int,
        guild_id: int,
    ) -> Dict[str, Any]:
        """Get punishment summary for user"""
        pass
    
    @abstractmethod
    async def check_auto_escalation(
        self,
        user_id: int,
        guild_id: int,
        new_punishment_type: PunishmentType,
    ) -> Optional[str]:
        """Check if auto-escalation should apply (e.g., 3 warns -> mute)"""
        pass
    
    @abstractmethod
    async def revoke_punishment(
        self,
        punishment_id: int,
        moderator_id: int,
        reason: str,
    ) -> bool:
        """Revoke a punishment (for admins)"""
        pass
    
    @abstractmethod
    async def export_punishments_csv(
        self,
        guild_id: int,
        *,
        since: Optional[datetime] = None,
    ) -> str:
        """Export punishments to CSV format"""
        pass

    @abstractmethod
    async def get(
        self,
        punishment_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get punishment by ID"""
        pass
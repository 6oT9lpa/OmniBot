from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any, Dict

from core.domain.value_objects import PunishmentType


@dataclass
class PunishmentDTO:
    """DTO for punishment record"""
    guild_id: int
    user_id: int
    moderator_id: int
    type: PunishmentType
    reason: str
    duration_seconds: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    retention_until: Optional[datetime] = None

    def to_db(self) -> Dict[str, Any]:
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "moderator_id": self.moderator_id,
            "type": self.type.value if isinstance(self.type, PunishmentType) else str(self.type),
            "reason": self.reason,
            "duration_seconds": self.duration_seconds,
            "expires_at": self.expires_at.isoformat(timespec="seconds") if self.expires_at else None,
            "is_active": 1 if self.is_active else 0,
            "retention_until": self.retention_until.isoformat(timespec="seconds") if self.retention_until else None,
        }


@dataclass
class PunishmentResultDTO:
    """Result of applying punishment"""
    success: bool
    punishment_id: Optional[int] = None
    user_id: Optional[int] = None
    punishment_type: Optional[PunishmentType] = None
    message: Optional[str] = None
    dm_sent: bool = False


def punishment_result_success(
    punishment_id: int,
    user_id: int,
    punishment_type: PunishmentType,
    dm_sent: bool = True,
) -> PunishmentResultDTO:
    return PunishmentResultDTO(
        success=True,
        punishment_id=punishment_id,
        user_id=user_id,
        punishment_type=punishment_type,
        dm_sent=dm_sent,
    )


def punishment_result_failure(message: str) -> PunishmentResultDTO:
    return PunishmentResultDTO(success=False, message=message)


@dataclass
class UserHistoryDTO:
    """DTO for user history"""
    user_id: int
    punishments: List[Dict[str, Any]]
    total_count: int
    active_count: int
    warning_count: int
    mute_count: int
    kick_count: int
    ban_count: int

    def get_summary(self) -> str:
        """Brief summary for embed"""
        return (
            f"**Violation Statistics:**\n"
            f"• Total: {self.total_count}\n"
            f"• Active: {self.active_count}\n"
            f"• Warnings: {self.warning_count}\n"
            f"• Mutes: {self.mute_count}\n"
            f"• Kicks: {self.kick_count}\n"
            f"• Bans: {self.ban_count}"
        )
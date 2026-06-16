from enum import Enum, auto
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


class PunishmentType(Enum):
    """Типы наказаний"""
    WARN = "warn"
    MUTE = "mute"
    UNMUTE = "unmute"
    KICK = "kick"
    BAN = "ban"
    UNBAN = "unban"
    TIMEOUT = "timeout" 
    
    def get_duration_human(self) -> str:
        """Человеко-читаемое представление"""
        durations = {
            PunishmentType.WARN: "перманентно",
            PunishmentType.MUTE: "временный",
            PunishmentType.KICK: "мгновенно",
            PunishmentType.BAN: "перманентно",
            PunishmentType.TIMEOUT: "временный",
            PunishmentType.UNBAN: "разбан",
            PunishmentType.UNMUTE: "размут"
        }
        return durations.get(self, "неизвестно")
    
    def requires_duration(self) -> bool:
        """Требует ли наказание указания длительности"""
        return self in [PunishmentType.MUTE, PunishmentType.TIMEOUT]


class EventType(Enum):
    """Типы событий сервера"""
    MEMBER_JOIN = "member_join"
    MEMBER_LEAVE = "member_leave"
    MEMBER_UPDATE = "member_update"
    CHANNEL_CREATE = "channel_create"
    CHANNEL_DELETE = "channel_delete"
    CHANNEL_UPDATE = "channel_update"
    ROLE_CREATE = "role_create"
    ROLE_DELETE = "role_delete"
    ROLE_UPDATE = "role_update"
    VOICE_JOIN = "voice_join"
    VOICE_LEAVE = "voice_leave"
    VOICE_MOVE = "voice_move"
    MESSAGE_DELETE_BULK = "message_delete_bulk"
    
    
@dataclass
class PunishmentInfo:
    """DTO для информации о наказании"""
    id: int
    user_id: int
    moderator_id: int
    punishment_type: PunishmentType
    reason: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    @property
    def is_expired(self) -> bool:
        """Проверить, истекло ли наказание"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at
    
    @property
    def time_left(self) -> Optional[str]:
        """Время до снятия наказания"""
        if not self.expires_at or self.is_expired:
            return None
        delta = self.expires_at - datetime.utcnow()
        return str(delta).split('.')[0]
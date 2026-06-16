# core/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.domain.value_objects import PunishmentType, EventType


@dataclass
class Message:
    """Бизнес-сущность сообщения"""
    id: int
    channel_id: int
    guild_id: int
    author_id: int
    content: str
    created_at: datetime
    edited_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    is_edited: bool = False
    is_deleted: bool = False
    ai_flagged: bool = False
    ai_reason: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    
    def was_modified_by_ai(self) -> bool:
        return self.ai_flagged
    
    def is_recent(self, hours: int = 24) -> bool:
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds() <= hours * 3600
    
    def mark_as_deleted(self) -> None:
        """Пометить сообщение как удалённое (доменная логика)"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def mark_as_edited(self, new_content: str) -> None:
        """Обновить содержимое (доменная логика)"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = datetime.utcnow()


@dataclass
class Punishment:
    """Бизнес-сущность наказания"""
    id: int
    user_id: int
    moderator_id: int
    guild_id: int
    punishment_type: PunishmentType
    reason: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at
    
    @property
    def time_left(self) -> Optional[str]:
        if not self.expires_at or self.is_expired:
            return None
        delta = self.expires_at - datetime.utcnow()
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}д {hours}ч"
        elif hours > 0:
            return f"{hours}ч {minutes}м"
        return f"{minutes}м"
    
    def expire(self) -> None:
        """Истечь (доменная логика)"""
        self.is_active = False
    
    def revoke(self) -> None:
        """Отозвать наказание (доменная логика)"""
        self.is_active = False
        self.expires_at = datetime.utcnow()


@dataclass
class GuildEvent:
    """Бизнес-сущность события сервера"""
    id: int
    guild_id: int
    event_type: EventType
    occurred_at: datetime
    user_id: Optional[int] = None
    target_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def get_readable_description(self) -> str:
        """Описание для логов (доменная логика)"""
        descriptions = {
            EventType.MEMBER_JOIN: "Присоединился к серверу",
            EventType.MEMBER_LEAVE: "Покинул сервер",
            EventType.CHANNEL_CREATE: "Создан канал",
            EventType.CHANNEL_DELETE: "Удалён канал",
            EventType.ROLE_CREATE: "Создана роль",
            EventType.ROLE_DELETE: "Удалена роль",
            EventType.VOICE_JOIN: "Зайшёл в голосовой канал",
            EventType.VOICE_LEAVE: "Вышел из голосового канала",
        }
        return descriptions.get(self.event_type, "Произошло событие")


@dataclass
class ModerationConfig:
    """Конфигурация модерации (бизнес-правила)"""
    guild_id: int
    warn_limit: int = 3
    mute_duration: int = 600
    auto_escalation: bool = True
    log_channel_id: Optional[int] = None
    deleted_messages_channel_id: Optional[int] = None
    send_dm_notifications: bool = True
    
    def should_auto_mute(self, warning_count: int) -> bool:
        """Бизнес-правило: нужно ли автоматически замутить"""
        return self.auto_escalation and warning_count >= self.warn_limit
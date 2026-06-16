from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any, Dict


@dataclass
class MessageLogDTO:
    """DTO для передачи логов сообщений"""
    guild_id: int
    message_id: int
    author_id: int
    author_name: str
    channel_id: int
    content: str
    created_at: datetime
    event_type: str = "message"
    is_deleted: bool = False
    is_edited: bool = False
    ai_flagged: bool = False
    retention_until: Optional[datetime] = None

    def truncate_content(self, max_length: int = 100) -> str:
        """Обрезать контент (утилитарный метод)"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

    def to_db(self) -> Dict[str, Any]:
        return {
            "guild_id": self.guild_id,
            "message_id": self.message_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "channel_id": self.channel_id,
            "content": self.content,
            "event_type": self.event_type,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "retention_until": self.retention_until.isoformat(timespec="seconds") if self.retention_until else None,
        }


@dataclass
class GuildEventLogDTO:
    """DTO для логов событий сервера"""
    guild_id: int
    event_type: str
    created_at: datetime
    channel_id: Optional[int] = None
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    details: Optional[str] = None
    retention_until: Optional[datetime] = None

    def to_db(self) -> Dict[str, Any]:
        return {
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "event_type": self.event_type,
            "details": self.details,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "retention_until": self.retention_until.isoformat(timespec="seconds") if self.retention_until else None,
        }


@dataclass
class DeletedMessageDTO:
    """DTO для удалённого сообщения (между сервисом и presentation)"""
    message_id: int
    channel_id: int
    author_id: int
    author_name: str
    content: str
    deleted_at: datetime
    deleted_by: Optional[int] = None
    attachments: List[str] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass
class EditedMessageDTO:
    """DTO для отредактированного сообщения"""
    message_id: int
    channel_id: int
    author_id: int
    before_content: str
    after_content: str
    edited_at: datetime


@dataclass
class BulkDeleteDTO:
    """DTO для массового удаления"""
    channel_id: int
    message_ids: List[int]
    deleted_by: Optional[int]
    deleted_at: datetime
    
    @property
    def count(self) -> int:
        return len(self.message_ids)
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class VoiceRoomDTO:
    """DTO голосовой комнаты."""

    channel_id: int
    guild_id: int
    owner_id: int
    name: str
    admin_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_persistent: bool = False

    def to_db(self) -> Dict[str, Any]:
        return {
            "channel_id":    self.channel_id,
            "guild_id":      self.guild_id,
            "owner_id":      self.owner_id,
            "admin_id":      self.admin_id,
            "name":          self.name,
            "created_at":    self.created_at.isoformat(timespec="seconds"),
            "is_persistent": int(self.is_persistent),
        }


@dataclass
class VoiceRoomTransferDTO:
    """DTO передачи владения комнатой."""

    channel_id: int
    old_admin_id: int | None
    new_admin_id: int | None
    transferred_at: datetime = field(default_factory=datetime.utcnow)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CreatorPlatform(str, Enum):
    TWITCH = "twitch"
    YOUTUBE = "youtube"
    KICK = "kick"


class CreatorAlertKind(str, Enum):
    STREAM = "stream"
    VIDEO = "video"
    SHORT = "short"


@dataclass(frozen=True)
class CreatorAlertSubscription:
    id: Optional[int]
    guild_id: int
    user_id: int
    platform: CreatorPlatform
    channel_url: str
    channel_name: Optional[str] = None
    external_channel_id: Optional[str] = None
    alert_kind: CreatorAlertKind = CreatorAlertKind.STREAM
    title_template: str = "{creator.name} is live on {platform}"
    description_template: str = "{creator.ping} {creator.name} started streaming {game}\n{url}"
    button_label: str = "Watch"
    color: int = 0x5865F2
    ping_role_id: Optional[int] = None
    active: bool = True
    last_event_id: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def uses_custom_template(self) -> bool:
        return bool(self.title_template and self.description_template)


@dataclass(frozen=True)
class CreatorContentEvent:
    platform: CreatorPlatform
    alert_kind: CreatorAlertKind
    event_id: str
    creator_name: str
    title: str
    url: str
    game: Optional[str] = None
    thumbnail_url: Optional[str] = None
    started_at: Optional[datetime] = None

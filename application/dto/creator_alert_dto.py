from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.domain.creator_alert import CreatorAlertKind, CreatorPlatform


@dataclass(frozen=True)
class CreatorAlertSubscriptionInput:
    guild_id: int
    user_id: int
    platform: CreatorPlatform
    channel_url: str
    channel_name: Optional[str] = None
    external_channel_id: Optional[str] = None
    alert_kind: CreatorAlertKind = CreatorAlertKind.STREAM
    title_template: Optional[str] = None
    description_template: Optional[str] = None
    button_label: str = "Watch"
    color: int = 0x5865F2
    ping_role_id: Optional[int] = None
    active: bool = True

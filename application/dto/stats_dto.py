from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class UserStatsDTO:
    """DTO статистики одного пользователя."""

    user_id: int
    guild_id: int
    messages_count: int = 0
    voice_minutes: int = 0
    warnings_count: int = 0
    last_message: Optional[datetime] = None
    joined_at: Optional[datetime] = None


@dataclass
class ServerStatsDTO:
    """DTO общей статистики сервера за период."""

    guild_id: int
    period_days: int
    total_messages: int = 0
    active_users: int = 0
    active_channels: int = 0
    avg_per_day: float = 0.0
    top_user_id: Optional[int] = None
    top_user_count: int = 0
    top_channel_id: Optional[int] = None
    top_channel_count: int = 0
    top_hour: Optional[int] = None
    top_hour_count: int = 0
    daily_stats: List[Dict[str, Any]] = field(default_factory=list)
    voice_users: int = 0
    total_voice_minutes: int = 0
    top_voice: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MessageHistoryDTO:
    """DTO одной записи в истории сообщений."""

    message_id: int
    user_id: int
    guild_id: int
    channel_id: int
    timestamp: datetime
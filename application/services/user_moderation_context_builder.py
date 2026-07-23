from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.dto.user_moderation_context import UserModerationContext, UserPunishmentStatistics
from core.interfaces.repositories.ai_moderation_repository_interface import AiModerationRepositoryInterface
from core.interfaces.repositories.punishment_repository_interface import PunishmentRepositoryInterface


class UserModerationContextBuilder:
    def __init__(self, punishments: PunishmentRepositoryInterface, moderation_events: AiModerationRepositoryInterface) -> None:
        self._punishments = punishments
        self._moderation_events = moderation_events

    async def build(self, member: object, guild_id: int, user_id: int, window_days: int) -> UserModerationContext:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=window_days)
        rows = await self._punishments.list_for_user(guild_id, user_id, limit=500)
        in_window = [row for row in rows if (created := self._created_at(row)) and created >= since]
        ai_deleted = await self._moderation_events.count_ai_deleted_messages(guild_id, user_id, since)
        types = [str(row.get("type", "")).casefold() for row in in_window]
        account_created_at = self._aware(getattr(getattr(member, "user", member), "created_at", None))
        joined_guild_at = self._aware(getattr(member, "joined_at", None))
        return UserModerationContext(
            account_created_at=account_created_at,
            joined_guild_at=joined_guild_at,
            account_age_days=self._age_days(now, account_created_at),
            guild_membership_days=self._age_days(now, joined_guild_at),
            punishments=UserPunishmentStatistics(
                window_days=window_days,
                total_in_window=len(in_window) + ai_deleted,
                timeouts_in_window=sum(item in {"timeout", "mute"} for item in types),
                ai_deleted_messages_in_window=ai_deleted,
                bans_in_window=types.count("ban"),
                last_punishment_at=max((self._created_at(row) for row in rows if self._created_at(row)), default=None),
            ),
        )

    def _created_at(self, row: dict[str, object]) -> datetime | None:
        value = row.get("created_at")
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return None
        return self._aware(value if isinstance(value, datetime) else None)

    def _aware(self, value: datetime | None) -> datetime | None:
        return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _age_days(self, now: datetime, value: datetime | None) -> int | None:
        return max(0, (now - value).days) if value else None

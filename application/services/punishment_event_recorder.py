from __future__ import annotations

from datetime import datetime

from core.domain.value_objects import PunishmentType
from core.interfaces.repositories.punishment_repository_interface import PunishmentRepositoryInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PunishmentEventRecorder:
    """Persists Discord audit events used by moderation-context aggregation."""

    def __init__(self, punishments: PunishmentRepositoryInterface) -> None:
        self._punishments = punishments

    async def record_ban(
        self,
        *,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        audit_entry_id: int,
        reason: str,
    ) -> None:
        await self._record(
            guild_id=guild_id,
            user_id=user_id,
            moderator_id=moderator_id,
            audit_entry_id=audit_entry_id,
            punishment_type=PunishmentType.BAN,
            reason=reason,
        )

    async def record_timeout(
        self,
        *,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        audit_entry_id: int,
        reason: str,
        duration_seconds: int,
        expires_at: datetime | None,
    ) -> None:
        await self._record(
            guild_id=guild_id,
            user_id=user_id,
            moderator_id=moderator_id,
            audit_entry_id=audit_entry_id,
            punishment_type=PunishmentType.TIMEOUT,
            reason=reason,
            duration_seconds=max(0, duration_seconds),
            expires_at=expires_at,
        )

    async def _record(
        self,
        *,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        audit_entry_id: int,
        punishment_type: PunishmentType,
        reason: str,
        duration_seconds: int | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        if min(guild_id, user_id, audit_entry_id) <= 0:
            logger.warning(
                "Punishment audit event ignored due to invalid identity guild_id=%s user_id=%s audit_entry_id=%s",
                guild_id,
                user_id,
                audit_entry_id,
            )
            return
        await self._punishments.add_punishment(
            user_id=user_id,
            moderator_id=max(0, moderator_id),
            punishment_type=punishment_type,
            reason=reason,
            guild_id=guild_id,
            duration=duration_seconds,
            expires_at=expires_at,
            message_id=audit_entry_id,
            source="HUMAN",
        )
        logger.info(
            "Punishment audit event recorded guild_id=%s user_id=%s audit_entry_id=%s type=%s",
            guild_id,
            user_id,
            audit_entry_id,
            punishment_type.value,
        )

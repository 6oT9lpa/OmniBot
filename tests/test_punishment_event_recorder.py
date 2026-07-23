from datetime import datetime, timezone

import pytest

from application.services.punishment_event_recorder import PunishmentEventRecorder
from core.domain.value_objects import PunishmentType


class _PunishmentRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def add_punishment(self, **kwargs) -> int:
        self.calls.append(kwargs)
        return 1


@pytest.mark.asyncio
async def test_records_human_ban_with_audit_event_identity() -> None:
    repository = _PunishmentRepository()

    await PunishmentEventRecorder(repository).record_ban(
        guild_id=10,
        user_id=20,
        moderator_id=30,
        audit_entry_id=40,
        reason="reason",
    )

    assert repository.calls == [{
        "user_id": 20,
        "moderator_id": 30,
        "punishment_type": PunishmentType.BAN,
        "reason": "reason",
        "guild_id": 10,
        "duration": None,
        "expires_at": None,
        "message_id": 40,
        "source": "HUMAN",
    }]


@pytest.mark.asyncio
async def test_records_timeout_with_duration_and_expiry() -> None:
    repository = _PunishmentRepository()
    expiry = datetime(2026, 7, 24, tzinfo=timezone.utc)

    await PunishmentEventRecorder(repository).record_timeout(
        guild_id=10,
        user_id=20,
        moderator_id=30,
        audit_entry_id=41,
        reason="timeout",
        duration_seconds=-10,
        expires_at=expiry,
    )

    assert repository.calls[0]["punishment_type"] is PunishmentType.TIMEOUT
    assert repository.calls[0]["duration"] == 0
    assert repository.calls[0]["expires_at"] == expiry


@pytest.mark.asyncio
async def test_ignores_event_without_stable_identity() -> None:
    repository = _PunishmentRepository()

    await PunishmentEventRecorder(repository).record_ban(
        guild_id=10,
        user_id=20,
        moderator_id=30,
        audit_entry_id=0,
        reason="reason",
    )

    assert repository.calls == []

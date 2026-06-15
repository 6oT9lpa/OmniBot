import pytest

from application.services import ModerationHistoryService
from core.domain.value_objects import PunishmentType


class FakePunishmentRepository:
    def __init__(self, rows):
        self.rows = rows

    async def list_for_user(self, guild_id, user_id, limit=50):
        return self.rows

    async def list_active(self, guild_id, punishment_type=None, limit=50):
        rows = [row for row in self.rows if row.get("is_active")]
        if punishment_type:
            rows = [row for row in rows if row.get("type") == punishment_type]
        return rows[:limit]

    async def get(self, punishment_id):
        for row in self.rows:
            if row["id"] == punishment_id:
                return row
        return None

    async def deactivate(self, punishment_id):
        for row in self.rows:
            if row["id"] == punishment_id:
                row["is_active"] = 0
                return True
        return False

    async def revoke_punishment(self, punishment_id, revoked_by):
        for row in self.rows:
            if row["id"] == punishment_id:
                row["is_active"] = 0
                row.setdefault("reason", "")
                row["reason"] = row["reason"] + f" | revoked_by={revoked_by}"
                return True
        return False


@pytest.mark.asyncio
async def test_three_active_warnings_trigger_mute_recommendation():
    repo = FakePunishmentRepository([
        {"id": i, "guild_id": 1, "user_id": 42, "type": PunishmentType.WARN.value, "is_active": 1}
        for i in range(1, 4)
    ])
    service = ModerationHistoryService(repo)

    escalation = await service.check_auto_escalation(42, 1, PunishmentType.WARN)

    assert "3 warnings" in escalation


@pytest.mark.asyncio
async def test_three_active_mutes_trigger_kick_recommendation():
    repo = FakePunishmentRepository([
        {"id": i, "guild_id": 1, "user_id": 42, "type": PunishmentType.MUTE.value, "is_active": 1}
        for i in range(1, 4)
    ])
    service = ModerationHistoryService(repo)

    escalation = await service.check_auto_escalation(42, 1, PunishmentType.MUTE)

    assert "3 mutes" in escalation


@pytest.mark.asyncio
async def test_two_kicks_trigger_ban_recommendation():
    repo = FakePunishmentRepository([
        {"id": i, "guild_id": 1, "user_id": 42, "type": PunishmentType.KICK.value, "is_active": 1}
        for i in range(1, 3)
    ])
    service = ModerationHistoryService(repo)

    escalation = await service.check_auto_escalation(42, 1, PunishmentType.KICK)

    assert "2 kicks" in escalation


@pytest.mark.asyncio
async def test_revoke_punishment_deactivates_record():
    repo = FakePunishmentRepository([
        {"id": 7, "guild_id": 1, "user_id": 42, "type": PunishmentType.MUTE.value, "is_active": 1}
    ])
    service = ModerationHistoryService(repo)

    ok = await service.revoke_punishment(7, 99, "error")

    assert ok is True
    assert repo.rows[0]["is_active"] == 0


@pytest.mark.asyncio
async def test_get_returns_punishment():
    repo = FakePunishmentRepository([
        {"id": 7, "guild_id": 1, "user_id": 42, "type": PunishmentType.MUTE.value, "is_active": 1}
    ])
    service = ModerationHistoryService(repo)

    punishment = await service.get(7)

    assert punishment is not None
    assert punishment["id"] == 7


@pytest.mark.asyncio
async def test_get_returns_none_for_invalid_id():
    repo = FakePunishmentRepository([])
    service = ModerationHistoryService(repo)

    punishment = await service.get(999)

    assert punishment is None
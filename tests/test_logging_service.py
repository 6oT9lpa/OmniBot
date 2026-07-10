from datetime import datetime, timezone

import pytest

from application.dto.logging_dto import MessageLogDTO
from application.services import LoggingService
from core.domain.value_objects import EventType


class FakeMessageLogRepository:
    def __init__(self):
        self.rows = []

    async def add(self, dto):
        self.rows.append(dto)
        return len(self.rows)

    async def cleanup_expired(self, cutoff_iso):
        before = len(self.rows)
        self.rows = [row for row in self.rows if not row.retention_until or row.retention_until.isoformat() >= cutoff_iso]
        return before - len(self.rows)


class FakeGuildEventLogRepository:
    def __init__(self):
        self.rows = []

    async def add(self, dto):
        self.rows.append(dto)
        return len(self.rows)

    async def cleanup_expired(self, cutoff_iso):
        before = len(self.rows)
        self.rows = [row for row in self.rows if not row.retention_until or row.retention_until.isoformat() >= cutoff_iso]
        return before - len(self.rows)


class FakeAuditLogService:
    def __init__(self):
        self.embeds = []

    async def send_to_log_channel(self, guild_id, embed, *, channel_id=None):
        self.embeds.append((guild_id, embed, channel_id))


@pytest.mark.asyncio
async def test_log_message_writes_database_dto_and_discord_embed():
    message_repo = FakeMessageLogRepository()
    guild_repo = FakeGuildEventLogRepository()
    audit = FakeAuditLogService()
    service = LoggingService(message_repo, guild_repo, audit, config=None)
    service._config = type("Config", (), {"message_log_retention_days": 30})()
    service._message_retention_until = lambda: datetime(2026, 1, 2, tzinfo=timezone.utc)
    service._event_retention_until = lambda: datetime(2026, 1, 2, tzinfo=timezone.utc)

    message = type("Message", (), {
        "guild": type("Guild", (), {"id": 1})(),
        "author": type("Author", (), {"id": 2, "__str__": lambda self: "user"})(),
        "channel": type("Channel", (), {"id": 3})(),
        "id": 4,
        "content": "hello",
    })()

    await service.log_message(message)

    assert message_repo.rows[0].event_type == "message"
    assert message_repo.rows[0].content == "hello"
    assert guild_repo.rows[0].event_type == "message"
    assert len(audit.embeds) == 1


@pytest.mark.asyncio
async def test_log_member_join_is_skipped():
    message_repo = FakeMessageLogRepository()
    guild_repo = FakeGuildEventLogRepository()
    audit = FakeAuditLogService()
    service = LoggingService(message_repo, guild_repo, audit, config=None)
    service._config = type("Config", (), {"message_log_retention_days": 30})()
    service._event_retention_until = lambda: datetime(2026, 1, 2, tzinfo=timezone.utc)

    member = type("Member", (), {
        "guild": type("Guild", (), {"id": 1})(),
        "id": 2,
        "__str__": lambda self: "user",
    })()

    await service.log_member_event(EventType.MEMBER_JOIN, member)

    assert len(guild_repo.rows) == 0
    assert len(audit.embeds) == 0


@pytest.mark.asyncio
async def test_log_member_update_uses_member_event_embed():
    message_repo = FakeMessageLogRepository()
    guild_repo = FakeGuildEventLogRepository()
    audit = FakeAuditLogService()
    service = LoggingService(message_repo, guild_repo, audit, config=None)
    service._config = type("Config", (), {"message_log_retention_days": 30})()

    member = type("Member", (), {
        "guild": type("Guild", (), {"id": 1})(),
        "id": 2,
        "mention": "<@2>",
        "joined_at": None,
        "roles": [],
        "__str__": lambda self: "user",
    })()

    await service.log_member_event(
        EventType.MEMBER_UPDATE,
        member,
        extra_data={"changes": ["pending: True -> False"]},
    )

    assert guild_repo.rows[0].event_type == "member_update"
    assert audit.embeds[0][1].title == "Проверка участника обновлена: user (ID: 2)"
    assert any(field.name == "Статус" and "ожидает проверки" in field.value for field in audit.embeds[0][1].fields)


def test_voice_admin_overwrite_change_is_suppressed_from_channel_update():
    service = LoggingService(FakeMessageLogRepository(), FakeGuildEventLogRepository(), FakeAuditLogService(), config=None)
    service._detect_voice_admin_overwrite_change = lambda before, after: "voice admin changed"

    before = type("Channel", (), {"name": "Room", "position": 1, "overwrites": {"old": object()}})()
    after = type("Channel", (), {"name": "Room", "position": 1, "overwrites": {"new": object()}})()

    assert service._detect_channel_changes(before, after) == []

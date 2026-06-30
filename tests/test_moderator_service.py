from datetime import timedelta

import pytest

from application.services.moderator_service import ModeratorService
from core.domain.value_objects import PunishmentType


class FakePermissions:
    def __init__(self, *, administrator=False):
        self.administrator = administrator


class FakeRole:
    def __init__(self, role_id, position, *, administrator=False, managed=False, default=False):
        self.id = role_id
        self.position = position
        self.permissions = FakePermissions(administrator=administrator)
        self.managed = managed
        self._default = default

    def is_default(self):
        return self._default


class FakeGuild:
    def __init__(self):
        self.id = 100
        self.me = None


class FakeMember:
    def __init__(
        self,
        member_id,
        guild,
        top_role,
        *,
        administrator=False,
        roles=None,
        name=None,
    ):
        self.id = member_id
        self.guild = guild
        self.top_role = top_role
        self.guild_permissions = FakePermissions(administrator=administrator)
        self.roles = roles or []
        self.name = name or f"user-{member_id}"
        self.removed_roles = []
        self.timeout_duration = None
        self.timeout_reason = None
        self.sent_messages = []

    async def remove_roles(self, *roles, reason=None):
        self.removed_roles.extend(roles)

    async def timeout(self, *, duration, reason):
        self.timeout_duration = duration
        self.timeout_reason = reason

    async def send(self, *, embed):
        self.sent_messages.append(embed)


class FakePunishmentRepository:
    async def add(self, punishment):
        assert punishment.type == PunishmentType.MUTE
        return 321


class FakeLoggingService:
    def __init__(self):
        self.actions = []

    async def log_moderation_action(self, *args, **kwargs):
        self.actions.append((args, kwargs))


class FakeHistoryService:
    async def check_auto_escalation(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_mute_admin_removes_admin_role_before_timeout():
    guild = FakeGuild()
    bot_role = FakeRole(1, 100)
    guild.me = FakeMember(10, guild, bot_role, administrator=True, roles=[bot_role], name="bot")
    moderator_role = FakeRole(2, 90, administrator=True)
    target_role = FakeRole(3, 50, administrator=True)
    moderator = FakeMember(
        20,
        guild,
        moderator_role,
        administrator=True,
        roles=[moderator_role],
        name="moderator",
    )
    target = FakeMember(
        30,
        guild,
        target_role,
        administrator=True,
        roles=[target_role],
        name="target",
    )
    service = ModeratorService(FakePunishmentRepository(), FakeLoggingService(), FakeHistoryService())

    result = await service.mute_user(
        moderator=moderator,
        target=target,
        reason="test mute",
        duration_seconds=120,
        send_dm=False,
    )

    assert result["success"] is True
    assert target.removed_roles == [target_role]
    assert target.timeout_duration == timedelta(seconds=120)
    assert target.timeout_reason == "test mute"


@pytest.mark.asyncio
async def test_duplicate_dm_notification_is_suppressed():
    guild = FakeGuild()
    target_role = FakeRole(3, 50)
    target = FakeMember(30, guild, target_role, name="target")
    service = ModeratorService(FakePunishmentRepository(), FakeLoggingService(), FakeHistoryService())

    first_sent = await service._send_dm(target, "User banned", "same reason")
    second_sent = await service._send_dm(target, "User banned", "same reason")

    assert first_sent is True
    assert second_sent is False
    assert len(target.sent_messages) == 1

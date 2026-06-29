import pytest

from application.services.voice_service import VoiceService


class FakePermissions:
    def __init__(self, *, manage_permissions=False):
        self.manage_permissions = manage_permissions


class FakeGuild:
    def __init__(self):
        self.members = {}
        self.default_role = object()

    def get_member(self, member_id):
        return self.members.get(member_id)


class FakeMember:
    def __init__(self, member_id, guild, *, bot=False, manage_permissions=False):
        self.id = member_id
        self.guild = guild
        self.bot = bot
        self.manage_permissions = manage_permissions
        self.display_name = f"user-{member_id}"
        self.mention = f"<@{member_id}>"
        self.voice = None
        guild.members[member_id] = self


class FakeChannel:
    def __init__(self, channel_id, guild):
        self.id = channel_id
        self.guild = guild
        self.permission_calls = []

    async def set_permissions(self, target, **kwargs):
        self.permission_calls.append((getattr(target, "id", target), kwargs))

    def permissions_for(self, user):
        return FakePermissions(manage_permissions=user.manage_permissions)


class FakeVoiceRepository:
    def __init__(self):
        self.room = {"channel_id": 10, "guild_id": 1, "owner_id": 42, "admin_id": None, "name": "Room"}

    async def get(self, channel_id):
        return dict(self.room) if channel_id == self.room["channel_id"] else None

    async def update_admin(self, channel_id, admin_id):
        assert channel_id == self.room["channel_id"]
        self.room["admin_id"] = admin_id


@pytest.mark.asyncio
async def test_owner_is_immutable_when_admin_is_assigned():
    repo = FakeVoiceRepository()
    service = VoiceService(repo)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    admin = FakeMember(99, guild)
    channel = FakeChannel(10, guild)

    await service.assign_admin(channel, admin, owner)

    assert repo.room["owner_id"] == 42
    assert repo.room["admin_id"] == 99
    assert channel.permission_calls[-1][0] == 99


@pytest.mark.asyncio
async def test_owner_cannot_claim_admin():
    repo = FakeVoiceRepository()
    service = VoiceService(repo)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    channel = FakeChannel(10, guild)

    with pytest.raises(PermissionError):
        await service.claim_admin(channel, owner)

    assert repo.room["owner_id"] == 42
    assert repo.room["admin_id"] is None


@pytest.mark.asyncio
async def test_admin_leave_clears_only_admin():
    repo = FakeVoiceRepository()
    repo.room["admin_id"] = 99
    service = VoiceService(repo)
    guild = FakeGuild()
    FakeMember(42, guild)
    admin = FakeMember(99, guild)
    channel = FakeChannel(10, guild)

    await service.handle_admin_leave(channel, admin)

    assert repo.room["owner_id"] == 42
    assert repo.room["admin_id"] is None
    assert channel.permission_calls[-1] == (99, {"overwrite": None})

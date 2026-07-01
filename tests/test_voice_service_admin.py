import asyncio

import pytest

from application.services.voice_service import VoiceService


class FakePermissions:
    def __init__(self, *, manage_permissions=False):
        self.manage_permissions = manage_permissions


class FakeGuild:
    def __init__(self):
        self.id = 1
        self.members = {}
        self.default_role = object()

    def get_member(self, member_id):
        return self.members.get(member_id)


class FakeVoiceState:
    def __init__(self, channel):
        self.channel = channel


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

    async def move_to(self, channel):
        current_channel = getattr(self.voice, "channel", self.voice)
        if current_channel and self in current_channel.members:
            current_channel.members.remove(self)
        if channel:
            if self not in channel.members:
                channel.members.append(self)
            self.voice = FakeVoiceState(channel)
        else:
            self.voice = None


class FakeChannel:
    def __init__(self, channel_id, guild):
        self.id = channel_id
        self.guild = guild
        self.permission_calls = []
        self.banned_ids = set()
        self.members = []

    async def set_permissions(self, target, **kwargs):
        self.permission_calls.append((getattr(target, "id", target), kwargs))

    def permissions_for(self, user):
        return FakePermissions(manage_permissions=user.manage_permissions)

    def overwrites_for(self, member):
        return type("Overwrite", (), {"connect": False if member.id in self.banned_ids else None})()


class FakeVoiceRepository:
    def __init__(self):
        self.room = {"channel_id": 10, "guild_id": 1, "owner_id": 42, "admin_id": None, "name": "Room"}
        self.added_members = []

    async def get(self, channel_id):
        return dict(self.room) if channel_id == self.room["channel_id"] else None

    async def update_admin(self, channel_id, admin_id):
        assert channel_id == self.room["channel_id"]
        self.room["admin_id"] = admin_id

    async def update_owner(self, channel_id, owner_id):
        assert channel_id == self.room["channel_id"]
        self.room["owner_id"] = owner_id

    async def add_member(self, channel_id, guild_id, user_id):
        self.added_members.append((channel_id, guild_id, user_id))

    async def remove_member(self, channel_id, user_id):
        pass

    async def clear_members(self, channel_id):
        pass

    async def get_member_ids(self, channel_id):
        return []


class FakeLoggingService:
    def __init__(self):
        self.owner_transfers = []

    async def log_voice_owner_transfer(self, channel, old_owner, new_owner):
        self.owner_transfers.append((channel.id, old_owner.id, new_owner.id))


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


@pytest.mark.asyncio
async def test_manage_permissions_cannot_assign_admin_without_owner():
    repo = FakeVoiceRepository()
    service = VoiceService(repo)
    guild = FakeGuild()
    moderator = FakeMember(77, guild, manage_permissions=True)
    target = FakeMember(99, guild)
    channel = FakeChannel(10, guild)

    with pytest.raises(PermissionError):
        await service.assign_admin(channel, target, moderator)

    assert repo.room["admin_id"] is None


@pytest.mark.asyncio
async def test_admin_cannot_kick_owner_or_self():
    repo = FakeVoiceRepository()
    repo.room["admin_id"] = 99
    service = VoiceService(repo)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    admin = FakeMember(99, guild)
    channel = FakeChannel(10, guild)

    with pytest.raises(PermissionError):
        await service.kick(channel, admin, admin)
    with pytest.raises(PermissionError):
        await service.ban(channel, owner, admin)

    assert channel.permission_calls == []


@pytest.mark.asyncio
async def test_ban_current_admin_clears_admin_before_denying_connect():
    repo = FakeVoiceRepository()
    repo.room["admin_id"] = 99
    service = VoiceService(repo)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    admin = FakeMember(99, guild)
    channel = FakeChannel(10, guild)

    await service.ban(channel, admin, owner)

    assert repo.room["admin_id"] is None
    assert channel.permission_calls == [
        (99, {"overwrite": None}),
        (99, {"connect": False}),
    ]


@pytest.mark.asyncio
async def test_banned_member_is_removed_on_join_without_tracking():
    repo = FakeVoiceRepository()
    service = VoiceService(repo)
    guild = FakeGuild()
    member = FakeMember(77, guild)
    channel = FakeChannel(10, guild)
    channel.banned_ids.add(77)
    member.voice = channel

    tracked = await service.track_member_join(channel, member)

    assert tracked is False
    assert member.voice is None
    assert repo.added_members == []


@pytest.mark.asyncio
async def test_owner_leave_transfers_owner_to_remaining_member():
    repo = FakeVoiceRepository()
    logging = FakeLoggingService()
    service = VoiceService(repo, logging)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    candidate = FakeMember(77, guild)
    channel = FakeChannel(10, guild)
    await candidate.move_to(channel)

    await service.schedule_owner_transfer(channel, owner, delay=0)
    await asyncio.sleep(0.05)

    assert repo.room["owner_id"] == 77
    assert channel.permission_calls == [
        (42, {"overwrite": None}),
        (77, {"connect": True, "manage_channels": True, "manage_permissions": True, "move_members": True}),
    ]
    assert logging.owner_transfers == [(10, 42, 77)]


@pytest.mark.asyncio
async def test_owner_transfer_is_cancelled_when_owner_returns():
    repo = FakeVoiceRepository()
    service = VoiceService(repo)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    candidate = FakeMember(77, guild)
    channel = FakeChannel(10, guild)
    await candidate.move_to(channel)

    await service.schedule_owner_transfer(channel, owner, delay=0.05)
    await owner.move_to(channel)
    tracked = await service.track_member_join(channel, owner)
    await asyncio.sleep(0.1)

    assert tracked is True
    assert repo.room["owner_id"] == 42


@pytest.mark.asyncio
async def test_owner_transfer_clears_admin_when_admin_becomes_owner():
    repo = FakeVoiceRepository()
    repo.room["admin_id"] = 77
    service = VoiceService(repo)
    guild = FakeGuild()
    owner = FakeMember(42, guild)
    candidate = FakeMember(77, guild)
    channel = FakeChannel(10, guild)
    await candidate.move_to(channel)

    await service.schedule_owner_transfer(channel, owner, delay=0)
    await asyncio.sleep(0.05)

    assert repo.room["owner_id"] == 77
    assert repo.room["admin_id"] is None

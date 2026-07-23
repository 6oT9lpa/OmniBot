import pytest
from application.services.moderation_labeling_service import ModerationLabelingService


class _Permissions:
    async def can_label(self, actor, guild): return actor == 1 and guild == 10


class _Repository:
    def __init__(self): self.labels = set(); self.audit_rows = []
    async def create_label(self, guild, channel, message, author, label, comment, actor, snapshot):
        key = (guild,message,label)
        if key in self.labels: return False
        self.labels.add(key); return True
    async def revoke_label(self, guild, message, label, actor): return (guild,message,label) in self.labels
    async def audit(self, *row): self.audit_rows.append(row)


class _ManagementRepository(_Repository):
    def __init__(self):
        super().__init__(); self.trusted = False; self.roles = []
    async def set_trusted(self, guild, enabled): self.trusted = enabled
    async def has_role(self, guild, actor, role): return (guild, actor, role) in self.roles
    async def assign_role(self, guild, user, role, actor): self.roles.append((guild, user, role))
    async def revoke_role(self, guild, user, role):
        item = (guild, user, role)
        if item not in self.roles: return False
        self.roles.remove(item); return True
    async def is_trusted(self, guild): return self.trusted
    async def list_roles(self, guild): return [{"user_id": user, "role": role} for current_guild, user, role in self.roles if current_guild == guild]


class _ManagementPermissions:
    async def is_owner(self, actor): return actor == 1
    async def can_manage(self, actor, guild): return actor == 1 or (guild == 10 and actor == 2)
    async def can_label(self, actor, guild): return False


@pytest.mark.asyncio
async def test_labeling_is_authorized_and_idempotent() -> None:
    repo = _Repository(); service = ModerationLabelingService(repo, _Permissions())
    assert await service.label(1,10,20,30,40,"spam")
    assert not await service.label(1,10,20,30,40,"spam")
    with pytest.raises(PermissionError): await service.label(2,10,20,30,40,"spam")
    assert repo.audit_rows[0][2] == "LABEL_CREATED"


@pytest.mark.asyncio
async def test_owner_and_guild_admin_scopes_are_enforced() -> None:
    repo = _ManagementRepository(); service = ModerationLabelingService(repo, _ManagementPermissions())
    await service.set_trusted(1, 10, True)
    await service.set_role(1, 10, 2, "ADMIN", True)
    await service.set_role(2, 10, 3, "LABELER", True)
    assert [row["user_id"] for row in await service.list_roles(2, 10)] == [2, 3]
    with pytest.raises(PermissionError):
        await service.set_role(2, 11, 4, "LABELER", True)
    with pytest.raises(PermissionError):
        await service.set_role(2, 10, 4, "ADMIN", True)


@pytest.mark.asyncio
async def test_roles_cannot_be_assigned_before_guild_is_trusted() -> None:
    repo = _ManagementRepository(); service = ModerationLabelingService(repo, _ManagementPermissions())

    with pytest.raises(PermissionError):
        await service.set_role(1, 10, 2, "ADMIN", True)

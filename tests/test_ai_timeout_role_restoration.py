import pytest

from presentation.cogs.ai_moderation_cog import AiModerationCog


class _Permissions:
    def __init__(self, administrator: bool):
        self.administrator = administrator


class _Role:
    def __init__(self, role_id: int, position: int, administrator: bool, *, managed: bool = False):
        self.id = role_id
        self.position = position
        self.permissions = _Permissions(administrator)
        self.managed = managed

    def is_default(self):
        return self.id == 0


class _Guild:
    def __init__(self, roles):
        self.me = type("BotMember", (), {"top_role": _Role(99, 50, False)})()
        self._roles = {role.id: role for role in roles}

    def get_role(self, role_id):
        return self._roles.get(role_id)


class _Member:
    def __init__(self, guild, roles):
        self.guild = guild
        self.roles = list(roles)
        self.removed = []
        self.added = []

    async def remove_roles(self, *roles, reason):
        self.removed.extend(roles)
        self.roles = [role for role in self.roles if role not in roles]

    async def add_roles(self, *roles, reason):
        self.added.extend(roles)
        self.roles.extend(roles)


@pytest.mark.asyncio
async def test_only_manageable_administrator_roles_are_removed_and_restored() -> None:
    manageable_admin = _Role(1, 10, True)
    higher_admin = _Role(2, 60, True)
    normal_role = _Role(3, 5, False)
    guild = _Guild((manageable_admin, higher_admin, normal_role))
    member = _Member(guild, (manageable_admin, higher_admin, normal_role))
    cog = object.__new__(AiModerationCog)

    removed_ids = await cog._remove_administrator_roles(member, "test")
    await cog._restore_roles(guild, member, removed_ids, "test")

    assert removed_ids == (1,)
    assert member.removed == [manageable_admin]
    assert member.added == [manageable_admin]
    assert higher_admin in member.roles

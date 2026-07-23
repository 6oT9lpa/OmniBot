import pytest

from application.services.labeling_permission_service import LabelingPermissionService


class _Repository:
    def __init__(self): self.roles = {(1, 20, "ADMIN"), (1, 30, "LABELER")}
    async def is_trusted(self, guild): return guild == 1
    async def has_role(self, guild, user, role): return (guild, user, role) in self.roles


@pytest.mark.asyncio
async def test_permissions_are_guild_scoped() -> None:
    service = LabelingPermissionService(_Repository(), 10)
    assert await service.can_manage(10, 2)
    assert await service.can_manage(20, 1)
    assert not await service.can_manage(20, 2)
    assert await service.can_label(30, 1)
    assert not await service.can_label(30, 2)

import pytest

from infrastructure.config import BotConfig
from infrastructure.database import DatabaseManager
from infrastructure.database.repositories.role_repository import RoleRepository
from infrastructure.database.repositories.voice_repository import VoiceRepository
from presentation.bot import DiscordBot


def test_discord_bot_registers_application_commands_globally():
    config = BotConfig(
        discord_token="test-token",
        discord_owner_id=1,
        database_url="sqlite:///test.db",
    )

    bot = DiscordBot(config)

    assert bot._test_guilds is None
    assert bot._command_sync_flags.sync_global_commands is False
    assert bot._command_sync_flags.sync_guild_commands is False


@pytest.mark.asyncio
async def test_role_repository_keeps_roles_scoped_by_guild(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'global_roles.db'}")
    await manager.initialize()
    repository = RoleRepository(manager)

    try:
        await repository.sync_from_discord(
            100,
            [
                {
                    "id": 10,
                    "name": "Alpha",
                    "color": 111,
                    "position": 1,
                }
            ],
        )
        await repository.sync_from_discord(
            200,
            [
                {
                    "id": 20,
                    "name": "Beta",
                    "color": 222,
                    "position": 1,
                }
            ],
        )

        await repository.set_auto_assign(10, True, 100)
        await repository.set_public(20, False, 200)

        guild_100_roles = await repository.get_all_roles(100)
        guild_200_roles = await repository.get_all_roles(200)

        assert [role["role_id"] for role in guild_100_roles] == [10]
        assert [role["role_id"] for role in guild_200_roles] == [20]
        assert await repository.get_auto_assign_roles(100) == [10]
        assert await repository.get_auto_assign_roles(200) == []
        assert await repository.get_public_roles(100)
        assert await repository.get_public_roles(200) == []
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_role_repository_requires_guild_without_legacy_default(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'missing_guild.db'}")
    await manager.initialize()
    repository = RoleRepository(manager)

    try:
        with pytest.raises(ValueError, match="guild_id is required"):
            await repository.get_all_roles()
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_voice_repository_tracks_members_per_channel(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'voice_members.db'}")
    await manager.initialize()
    repository = VoiceRepository(manager)

    try:
        await repository.add_member(10, 100, 42)
        await repository.add_member(10, 100, 99)
        await repository.add_member(20, 200, 77)

        assert await repository.get_member_ids(10) == [42, 99]

        await repository.remove_member(10, 42)
        assert await repository.get_member_ids(10) == [99]
        assert await repository.get_member_ids(20) == [77]

        await repository.clear_members(10)
        assert await repository.get_member_ids(10) == []
    finally:
        await manager.close()

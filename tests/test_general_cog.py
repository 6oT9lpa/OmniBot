from types import SimpleNamespace

from presentation.cogs.general_cog import GeneralCog


class _FakeBot:
    latency = 0.123


def _member(**permissions):
    defaults = {
        "administrator": False,
        "ban_members": False,
        "kick_members": False,
        "manage_channels": False,
        "manage_messages": False,
        "moderate_members": False,
    }
    defaults.update(permissions)
    return SimpleNamespace(guild_permissions=SimpleNamespace(**defaults))


def _commands_for(member):
    cog = GeneralCog(_FakeBot())
    sections = cog.get_available_commands_by_section(member)
    return {
        item["command"]
        for commands_in_section in sections.values()
        for item in commands_in_section
    }


def test_help_catalog_hides_moderation_and_admin_commands_from_regular_member():
    commands = _commands_for(_member())

    assert "/help" in commands
    assert "/ping" in commands
    assert "/stats user" in commands
    assert "/streamer add" in commands
    assert "Activity -> Creator Alerts" in commands
    assert "/ban" not in commands
    assert "/sync_roles" not in commands
    assert "/welcome setup" not in commands


def test_help_catalog_shows_permission_scoped_moderation_commands():
    commands = _commands_for(_member(moderate_members=True))

    assert "/warn" in commands
    assert "/history" in commands
    assert "/unmute" in commands
    assert "/ban" not in commands
    assert "/purge" not in commands


def test_help_catalog_shows_all_admin_commands_to_administrator():
    commands = _commands_for(_member(administrator=True))

    assert "/sync_roles" in commands
    assert "/voice set_trigger" in commands
    assert "/welcome setup" in commands
    assert "/activity_role" in commands
    assert "/set_role" in commands
    assert "/ban" in commands

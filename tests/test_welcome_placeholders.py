from datetime import datetime, timezone

from application.services.welcome_service import WelcomeService


class FakeWelcomeRepo:
    async def get_config(self, guild_id):
        return None


class FakeGuild:
    id = 100
    name = "Omni"
    member_count = 42


class FakeMember:
    id = 55
    display_name = "Sancheus"
    mention = "<@55>"
    joined_at = datetime(2026, 6, 30, 10, 15, tzinfo=timezone.utc)

    def __str__(self):
        return "Sancheus#0001"


def test_welcome_text_normalizes_supported_placeholders():
    service = WelcomeService(FakeWelcomeRepo())
    text = (
        "Hi {user} on {server} with {member_count} members at {joined_at}. "
        "{channel.123456789012345678} {role.123456789012345679} {user.123456789012345680}"
    )

    result = service.normalize_text(text, FakeMember(), FakeGuild())

    assert "Hi Sancheus on Omni with 42 members at 30.06.2026 10:15" in result
    assert "<#123456789012345678>" in result
    assert "<@&123456789012345679>" in result
    assert "<@123456789012345680>" in result

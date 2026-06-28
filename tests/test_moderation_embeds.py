from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from presentation.embeds import (
    ModerationBanEmbedBuilder,
    ModerationWarnEmbedBuilder,
    ModerationKickEmbedBuilder,
    ModerationMuteEmbedBuilder,
    ModerationTimeoutEmbedBuilder,
    format_date,
    format_duration_seconds,
)


class MockUser:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self._str = name

    def __str__(self):
        return self._str


def test_format_date():
    now = datetime.now(timezone.utc)
    formatted = format_date(now)
    assert formatted == now.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y")


def test_format_duration_seconds_permanent():
    assert format_duration_seconds(None) == "Permanent"


def test_format_duration_seconds_active():
    result = format_duration_seconds(86400)
    assert "until" in result
    assert "." in result


def test_ban_embed_builder_with_all_fields():
    target = MockUser(123456789, "TestUser")
    embed = ModerationBanEmbedBuilder.build_ban(
        target,
        duration_seconds=86400,
        delete_message_days=2,
        reason="Test reason",
    )
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0xED4245
    
    field_names = [f.name for f in embed.fields]
    assert "Banned User:" in field_names
    assert "Duration:" in field_names
    assert "Delete Message:" in field_names
    assert "Reason:" in field_names


def test_ban_embed_builder_without_duration():
    target = MockUser(123456789, "TestUser")
    embed = ModerationBanEmbedBuilder.build_ban(
        target,
        reason="Test reason",
    )
    
    field_names = [f.name for f in embed.fields]
    assert "Banned User:" in field_names
    assert "Reason:" in field_names
    assert "Duration:" not in field_names


def test_unban_embed_builder():
    target = MockUser(123456789, "TestUser")
    embed = ModerationBanEmbedBuilder.build_unban(target, reason="Test unban reason")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0x57F287
    
    field_names = [f.name for f in embed.fields]
    assert "Unbanned User:" in field_names
    assert "Reason:" in field_names


def test_warn_embed_builder():
    target = MockUser(123456789, "TestUser")
    embed = ModerationWarnEmbedBuilder.build_warn(target, duration_seconds=3600, reason="Test warn reason")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0xFEE75C
    
    field_names = [f.name for f in embed.fields]
    assert "Warned User:" in field_names
    assert "Duration:" in field_names
    assert "Reason:" in field_names


def test_unwarn_embed_builder():
    target = MockUser(123456789, "TestUser")
    embed = ModerationWarnEmbedBuilder.build_unwarn(target, reason="Test unwarn reason")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0x57F287
    
    field_names = [f.name for f in embed.fields]
    assert "Unwarned User:" in field_names


def test_kick_embed_builder():
    target = MockUser(123456789, "TestUser")
    embed = ModerationKickEmbedBuilder.build_kick(target, reason="Test kick reason")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0xED4245
    
    field_names = [f.name for f in embed.fields]
    assert "Kicked User:" in field_names
    assert "Reason:" in field_names


def test_mute_embed_builder():
    target = MockUser(123456789, "TestUser")
    embed = ModerationMuteEmbedBuilder.build_mute(target, duration_seconds=600, reason="Test mute reason")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0x5865F2
    
    field_names = [f.name for f in embed.fields]
    assert "Muted User:" in field_names
    assert "Duration:" in field_names
    assert "Reason:" in field_names


def test_timeout_embed_builder():
    target = MockUser(123456789, "TestUser")
    embed = ModerationTimeoutEmbedBuilder.build_timeout(target, duration_seconds=300, reason="Test timeout reason")
    
    assert embed.title == "TestUser (123456789)"
    assert embed.color.value == 0x5865F2
    
    field_names = [f.name for f in embed.fields]
    assert "Timed out User:" in field_names
    assert "Duration:" in field_names
    assert "Reason:" in field_names

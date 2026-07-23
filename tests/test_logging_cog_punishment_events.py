from types import SimpleNamespace

import pytest

import presentation.cogs.logging_cog as logging_cog_module
from presentation.cogs.logging_cog import LoggingCog


class _LoggingService:
    async def log_audit_ban(self, **kwargs) -> None:
        self.ban = kwargs


class _Recorder:
    async def record_ban(self, **kwargs) -> None:
        self.ban = kwargs


@pytest.mark.asyncio
async def test_audit_ban_reaches_punishment_recorder(monkeypatch) -> None:
    class _DiscordUser:
        def __init__(self, user_id: int) -> None:
            self.id = user_id

    monkeypatch.setattr(logging_cog_module.disnake, "Member", _DiscordUser)
    monkeypatch.setattr(logging_cog_module.disnake, "User", _DiscordUser)
    logging_service = _LoggingService()
    recorder = _Recorder()
    cog = LoggingCog(object(), logging_service, object(), recorder)
    entry = SimpleNamespace(
        action=logging_cog_module.disnake.AuditLogAction.ban,
        target=_DiscordUser(20),
        user=_DiscordUser(30),
        guild=SimpleNamespace(id=10),
        id=40,
        reason="reason",
    )

    await cog.on_audit_log_entry_create(entry)

    assert recorder.ban == {
        "guild_id": 10,
        "user_id": 20,
        "moderator_id": 30,
        "audit_entry_id": 40,
        "reason": "reason",
    }

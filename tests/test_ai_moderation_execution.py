from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from application.dto.ai_moderation_decision import AiModerationDecision
from presentation.cogs.ai_moderation_cog import AiModerationCog


@pytest.mark.asyncio
async def test_delete_action_uses_discord_single_message_signature() -> None:
    """PartialMessage.delete must not receive an unsupported ``reason`` keyword."""
    calls = []

    class Message:
        id = 4

        async def delete(self):
            calls.append("deleted")

    class LoggingCog:
        def register_bot_message_deletion(self, message_id):
            calls.append(("registered", message_id))

    class Bot:
        def get_cog(self, name):
            return LoggingCog() if name == "LoggingCog" else None

    class Cog:
        _bot = Bot()

    decision = AiModerationDecision(
        event_id=1, guild_id=1, user_id=3, message_id=4, risk_score=90,
        action="DELETE", primary_label="SCAM", labels=("SCAM",),
        execution_plan=("DELETE",), dry_run=False,
    )

    await AiModerationCog._execute_action(Cog(), None, None, Message(), "DELETE", False, decision, object())

    assert calls == [("registered", 4), "deleted"]


@pytest.mark.asyncio
async def test_warning_dm_contains_moderation_context() -> None:
    sent = []

    class Member:
        id = 3

        async def send(self, *, embed):
            sent.append(embed)

    decision = AiModerationDecision(
        event_id=1, guild_id=1, user_id=3, message_id=4, risk_score=90,
        action="WARN", primary_label="THREAT", labels=("THREAT",),
        execution_plan=("WARN",), dry_run=False,
    )
    request = SimpleNamespace(channel_id=22, created_at=datetime(2026, 7, 23, 18, 44, tzinfo=timezone.utc))
    guild = SimpleNamespace(id=1, name="Test server")

    await AiModerationCog._send_warning_dm(object.__new__(AiModerationCog), Member(), guild, request, decision, "WARN")

    fields = {field.name: field.value for field in sent[0].fields}
    assert sent[0].title == "Предупреждение AI-модератора"
    assert fields["Сервер"] == "Test server"
    assert fields["Канал"] == "<#22>"
    assert fields["Причина"] == "Threat"

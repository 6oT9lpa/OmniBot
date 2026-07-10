import asyncio
from datetime import datetime, timezone

import pytest

from application.dto.ai_moderation_decision import AiModerationDecision
from application.dto.ai_moderation_request import AiModerationRequest
from application.services.ai_moderation_queue import AiModerationQueue
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class _AiClientStub:
    async def moderate(self, request: AiModerationRequest) -> AiModerationDecision:
        return AiModerationDecision(event_id=1, user_id=request.user_id, guild_id=request.guild_id, message_id=request.message_id, risk_score=73.5, action="DELETE", primary_label="SCAM", labels=("SCAM",), execution_plan=("DELETE",), dry_run=False)

    async def report_action(self, event_id: int, action: str, status: str, dry_run: bool) -> None:
        return None


@pytest.mark.asyncio
async def test_queue_delivers_decision_end_to_end() -> None:
    logger.info("AI queue test expected=one sanitized decision callback actual=queue dispatch")
    received: list[AiModerationDecision] = []
    completed = asyncio.Event()

    async def on_decision(_: AiModerationRequest, decision: AiModerationDecision) -> None:
        received.append(decision)
        completed.set()

    queue = AiModerationQueue(_AiClientStub(), 1, 1, on_decision)
    await queue.start()
    try:
        accepted = queue.submit(AiModerationRequest(guild_id=1, channel_id=2, user_id=3, message_id=4, raw_text="test content", created_at=datetime.now(timezone.utc)))
        await asyncio.wait_for(completed.wait(), timeout=1)
    finally:
        await queue.stop()
    assert accepted is True
    assert received[0].action == "DELETE"


@pytest.mark.asyncio
async def test_queue_is_bounded() -> None:
    logger.info("AI queue test expected=rejection when full actual=bounded queue")
    queue = AiModerationQueue(_AiClientStub(), 1, 1, lambda *_: asyncio.sleep(0))
    request = AiModerationRequest(guild_id=1, channel_id=2, user_id=3, message_id=4, raw_text="test content", created_at=datetime.now(timezone.utc))
    assert queue.submit(request) is True
    assert queue.submit(request.model_copy(update={"message_id": 5})) is False

from datetime import datetime, timezone

from application.dto.ai_moderation_request import AiModerationRequest
from infrastructure.ai.ai_moderator_api_client import AiModeratorApiClient


def test_ai_moderator_payload_serializes_discord_ids_as_strings() -> None:
    client = AiModeratorApiClient("http://127.0.0.1:8000", "key", 1)
    payload = client._moderation_payload(
        AiModerationRequest(
            guild_id=1150681470634049668,
            channel_id=1525175773722579145,
            user_id=762514681209946122,
            message_id=1525175773722579145,
            reply_to_message_id=1525175773722579144,
            raw_text="message",
            created_at=datetime.now(timezone.utc),
            mention_count=2,
        )
    )

    assert payload["platform"] == "discord"
    assert payload["guild_id"] == "1150681470634049668"
    assert payload["channel_id"] == "1525175773722579145"
    assert payload["user_id"] == "762514681209946122"
    assert payload["message_id"] == "1525175773722579145"
    assert payload["reply_to_message_id"] == "1525175773722579144"
    assert payload["mention_count"] == 2

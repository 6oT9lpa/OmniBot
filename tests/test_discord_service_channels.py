import pytest
from fastapi import HTTPException

from activity.server.services.discord_service import DiscordService


@pytest.mark.asyncio
async def test_moderation_channel_listing_includes_text_and_announcement_channels(monkeypatch) -> None:
    service = DiscordService()

    async def channels(*_: object) -> list[dict[str, object]]:
        return [
            {"id": "10", "name": "general", "type": 0, "position": 2},
            {"id": "11", "name": "news", "type": 5, "position": 1},
            {"id": "12", "name": "voice", "type": 2, "position": 0},
        ]

    monkeypatch.setattr(service, "_cached_bot_resource", channels)

    result = await service.list_channels("1", "moderation")

    assert [(channel.id, channel.type) for channel in result] == [("11", 5), ("10", 0)]


@pytest.mark.asyncio
async def test_moderation_channel_filter_drops_voice_channel(monkeypatch) -> None:
    service = DiscordService()

    async def channels(*_: object) -> list[dict[str, object]]:
        return [
            {"id": "10", "name": "general", "type": 0},
            {"id": "11", "name": "news", "type": 5},
            {"id": "12", "name": "voice", "type": 2},
        ]

    monkeypatch.setattr(service, "_cached_bot_resource", channels)

    assert await service.filter_moderation_channel_ids("1", {10, 11, 12}) == {10, 11}


@pytest.mark.asyncio
async def test_moderation_channel_validation_rejects_voice_channel(monkeypatch) -> None:
    service = DiscordService()

    async def channels(*_: object) -> list[dict[str, object]]:
        return [
            {"id": "10", "name": "general", "type": 0},
            {"id": "11", "name": "news", "type": 5},
            {"id": "12", "name": "voice", "type": 2},
        ]

    monkeypatch.setattr(service, "_cached_bot_resource", channels)

    await service.validate_moderation_channel_ids("1", {10, 11})

    with pytest.raises(HTTPException, match="message channels"):
        await service.validate_moderation_channel_ids("1", {12})

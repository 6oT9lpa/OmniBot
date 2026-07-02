import pytest
import disnake
from fastapi import HTTPException

import activity.server.dependencies as activity_dependencies
from activity.server.schemas.creator_alerts import CreatorAlertSourcePayload, CreatorAlertTestPayload
from activity.server.services.creator_alert_service import CreatorAlertService as ActivityCreatorAlertService
from activity.server.utils.creator_alert_messages import build_creator_alert_message
from application.dto.creator_alert_dto import CreatorAlertSubscriptionInput
from application.services.creator_alert_service import CreatorAlertService
from core.domain.creator_alert import CreatorAlertKind, CreatorContentEvent, CreatorPlatform
from infrastructure.api.twitch_client import TwitchClient
from infrastructure.api.url_parser import CreatorUrlParser
from infrastructure.api.youtube_client import YouTubeClient
from infrastructure.database import DatabaseManager
from infrastructure.database.repositories import ChannelConfigRepository, CreatorAlertRepository
from presentation.cogs.streams_cog import StreamsCog


class _RolePurposeService:
    async def get_role(self, guild_id, purpose):
        return 777


class _NoopClient:
    async def fetch_latest_event(self, channel_url, external_channel_id=None):
        return None


@pytest.fixture
def creator_event():
    return CreatorContentEvent(
        platform=CreatorPlatform.TWITCH,
        alert_kind=CreatorAlertKind.STREAM,
        event_id="evt-1",
        creator_name="Arnetik",
        title="Building OmniBot",
        url="https://twitch.tv/arnetik",
        game="Minecraft",
    )


def test_creator_alert_preview_renders_extended_placeholders(creator_event):
    payload = CreatorAlertTestPayload(
        guild_id=100,
        platform="twitch",
        channel_name=creator_event.creator_name,
        channel_url=creator_event.url,
        title_template="{creator.name} on {platform}",
        description_template="{creator.ping} {game} {url} {title}",
        ping_role_id=777,
        game=creator_event.game,
    )

    message = build_creator_alert_message(payload)

    assert message["content"] == "<@&777>"
    assert message["embeds"][0]["title"] == "Arnetik on Twitch"
    assert "<@&777> Minecraft https://twitch.tv/arnetik Preview alert" in message["embeds"][0]["description"]


def test_creator_url_parser_handles_twitch_and_youtube_urls():
    assert CreatorUrlParser.twitch_login("https://www.twitch.tv/stepiks_") == "stepiks_"
    assert CreatorUrlParser.twitch_login("stepiks_") == "stepiks_"
    assert CreatorUrlParser.youtube_channel_ref("https://www.youtube.com/@omni") == "@omni"
    assert CreatorUrlParser.youtube_channel_ref("https://www.youtube.com/channel/UC123") == "UC123"


def test_streaming_activity_game_uses_discord_state_not_title():
    cog = StreamsCog.__new__(StreamsCog)
    activity = disnake.Streaming(
        name="Twitch",
        details="Building OmniBot",
        state="Minecraft",
        url="https://www.twitch.tv/stepiks_",
    )

    assert cog._stream_title(activity) == "Building OmniBot"
    assert cog._stream_game(activity) == "Minecraft"
    assert cog._stream_url(activity) == "https://www.twitch.tv/stepiks_"


@pytest.mark.asyncio
async def test_platform_clients_skip_network_when_credentials_are_missing():
    twitch = TwitchClient(None, None)
    youtube = YouTubeClient(None)

    assert twitch.is_configured is False
    assert youtube.is_configured is False
    assert await twitch.fetch_latest_event("https://www.twitch.tv/stepiks_") is None
    assert await youtube.fetch_latest_event("https://www.youtube.com/@omni") is None


@pytest.mark.asyncio
async def test_creator_alert_service_enforces_five_sources_per_user(tmp_path):
    db = DatabaseManager(f"sqlite:///{tmp_path / 'creator_alerts.db'}")
    await db.initialize()
    try:
        repo = CreatorAlertRepository(db)
        channels = ChannelConfigRepository(db)
        service = CreatorAlertService(
            repo,
            channels,
            _RolePurposeService(),
            {CreatorPlatform.TWITCH: _NoopClient()},
        )

        for index in range(5):
            await service.save_source(
                CreatorAlertSubscriptionInput(
                    guild_id=100,
                    user_id=42,
                    platform=CreatorPlatform.TWITCH,
                    channel_url=f"https://twitch.tv/source{index}",
                )
            )

        with pytest.raises(ValueError):
            await service.save_source(
                CreatorAlertSubscriptionInput(
                    guild_id=100,
                    user_id=42,
                    platform=CreatorPlatform.YOUTUBE,
                    channel_url="https://youtube.com/@sixth",
                )
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_activity_creator_alert_service_applies_default_ping_role(tmp_path, monkeypatch):
    db = DatabaseManager(f"sqlite:///{tmp_path / 'activity_creator_alerts.db'}")
    await db.initialize()
    previous_db = activity_dependencies._db
    previous_role_service = activity_dependencies._role_purpose_service
    activity_dependencies._db = db
    activity_dependencies._role_purpose_service = _RolePurposeService()
    service = ActivityCreatorAlertService()

    async def ensure_access(*_):
        return {"id": "42", "username": "creator"}, {"is_admin": False, "is_streamer": True}

    monkeypatch.setattr(service._access_service, "ensure_module_access", ensure_access)
    try:
        saved = await service.save_source(
            CreatorAlertSourcePayload(
                guild_id=100,
                platform="twitch",
                channel_url="https://twitch.tv/creator",
                channel_name="Creator",
            ),
            "token",
        )

        assert saved["ping_role_id"] == "777"
        assert saved["user_id"] == "42"
    finally:
        activity_dependencies._db = previous_db
        activity_dependencies._role_purpose_service = previous_role_service
        await db.close()


@pytest.mark.asyncio
async def test_activity_creator_alert_service_rejects_sixth_source(tmp_path, monkeypatch):
    db = DatabaseManager(f"sqlite:///{tmp_path / 'activity_creator_alerts_limit.db'}")
    await db.initialize()
    previous_db = activity_dependencies._db
    previous_role_service = activity_dependencies._role_purpose_service
    activity_dependencies._db = db
    activity_dependencies._role_purpose_service = _RolePurposeService()
    service = ActivityCreatorAlertService()

    async def ensure_access(*_):
        return {"id": "42", "username": "creator"}, {"is_admin": False, "is_streamer": True}

    monkeypatch.setattr(service._access_service, "ensure_module_access", ensure_access)
    try:
        for index in range(5):
            await service.save_source(
                CreatorAlertSourcePayload(
                    guild_id=100,
                    platform="twitch",
                    channel_url=f"https://twitch.tv/creator{index}",
                ),
                "token",
            )

        with pytest.raises(HTTPException) as exc_info:
            await service.save_source(
                CreatorAlertSourcePayload(
                    guild_id=100,
                    platform="youtube",
                    channel_url="https://youtube.com/@sixth",
                ),
                "token",
            )
        assert exc_info.value.status_code == 400
    finally:
        activity_dependencies._db = previous_db
        activity_dependencies._role_purpose_service = previous_role_service
        await db.close()

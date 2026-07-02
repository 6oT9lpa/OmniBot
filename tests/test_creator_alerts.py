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
from presentation.embeds.creator_alert_embed import CreatorAlertEmbedBuilder
from presentation.cogs.streams_cog import StreamsCog


class _RolePurposeService:
    async def get_role(self, guild_id, purpose):
        return 777


class _NoopClient:
    is_configured = True

    async def fetch_latest_event(self, channel_url, external_channel_id=None):
        return None


class _MissingCredentialsClient(_NoopClient):
    is_configured = False


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

    assert message["content"] == "||<@&777>||"
    assert message["embeds"][0]["title"] == "Arnetik on Twitch"
    assert "||<@&777>|| Minecraft https://twitch.tv/arnetik Preview alert" in message["embeds"][0]["description"]
    assert message["components"][0]["components"][0]["label"] == "Watch"
    assert message["components"][0]["components"][0]["url"] == "https://twitch.tv/arnetik"


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
    assert cog._stream_thumbnail_url(activity).endswith("live_user_stepiks_-1280x720.jpg")


def test_youtube_streaming_activity_uses_youtube_platform_and_thumbnail():
    cog = StreamsCog.__new__(StreamsCog)
    activity = disnake.Streaming(
        name="YouTube",
        details="Моя трансляция",
        state="Not specified",
        url="https://youtube.com/watch?v=bhu63w-yd9k",
    )

    assert cog._stream_platform(activity) == CreatorPlatform.YOUTUBE
    assert cog._stream_thumbnail_url(activity) == "https://img.youtube.com/vi/bhu63w-yd9k/maxresdefault.jpg"


@pytest.mark.asyncio
async def test_streaming_activity_scan_publishes_existing_status_once():
    class Guild:
        id = 100
        members = []

    class Member:
        id = 42
        bot = False
        guild = Guild()
        display_name = "Creator"
        activities = [
            disnake.Streaming(
                name="Twitch",
                details="Building OmniBot",
                state="Minecraft",
                url="https://www.twitch.tv/creator",
            )
        ]

    class Service:
        async def list_sources(self, guild_id, user_id=None):
            return []

    Guild.members = [Member()]
    cog = StreamsCog.__new__(StreamsCog)
    cog._creator_alert_service = Service()
    cog._fallback_event_ids = set()
    published = []

    async def publish_default(guild, user_id, event):
        published.append((guild.id, user_id, event))

    cog._publish_default_event = publish_default

    await cog._scan_discord_streaming_members(Guild())
    await cog._scan_discord_streaming_members(Guild())

    assert len(published) == 1
    assert published[0][0] == 100
    assert published[0][1] == 42
    assert published[0][2].title == "Building OmniBot"
    assert published[0][2].game == "Minecraft"


def test_default_creator_alert_embed_is_russian_and_visual(creator_event):
    event = CreatorContentEvent(
        platform=CreatorPlatform.TWITCH,
        alert_kind=CreatorAlertKind.STREAM,
        event_id="evt-2",
        creator_name="Gadj",
        title="я чемпион",
        url="https://www.twitch.tv/n1gadjiga",
        game="Minecraft",
        thumbnail_url="https://static-cdn.jtvnw.net/previews-ttv/live_user_gadj-1280x720.jpg",
    )

    embed = CreatorAlertEmbedBuilder.build(
        event,
        title_template="{creator.name} is live on {platform}",
        description_template="{creator.ping} {title}\nGame: {game}\n{url}",
        creator_ping="@stream ping",
        creator_icon_url="https://cdn.discordapp.com/avatars/1/avatar.png",
    )
    payload = embed.to_dict()

    assert payload["title"] == "Gadj начал стрим на Twitch"
    assert "уже в эфире" in payload["description"]
    assert "Категория" in payload["fields"][1]["name"]
    assert payload["author"]["icon_url"] == "https://cdn.discordapp.com/avatars/1/avatar.png"
    assert payload["image"]["url"].endswith("live_user_gadj-1280x720.jpg")
    assert payload["footer"]["icon_url"].endswith("live_user_gadj-1280x720.jpg")


def test_youtube_stream_embed_has_platform_specific_copy():
    event = CreatorContentEvent(
        platform=CreatorPlatform.YOUTUBE,
        alert_kind=CreatorAlertKind.STREAM,
        event_id="yt-live-1",
        creator_name="Санчеус",
        title="Моя трансляция",
        url="https://youtube.com/watch?v=bhu63w-yd9k",
        game="Just Chatting",
        thumbnail_url="https://img.youtube.com/vi/bhu63w-yd9k/maxresdefault.jpg",
    )

    embed = CreatorAlertEmbedBuilder.build(
        event,
        title_template="",
        description_template="",
        creator_ping="@stream ping",
    )
    payload = embed.to_dict()

    assert payload["title"] == "Санчеус начал стрим на YouTube"
    assert "прямой эфир на YouTube" in payload["description"]
    assert "ставь лайк" in payload["description"]
    assert payload["fields"][0]["value"] == "YouTube"
    assert payload["image"]["url"].endswith("bhu63w-yd9k/maxresdefault.jpg")


@pytest.mark.asyncio
async def test_platform_clients_skip_network_when_credentials_are_missing():
    twitch = TwitchClient(None, None)
    youtube = YouTubeClient(None)

    assert twitch.is_configured is False
    assert youtube.is_configured is False
    assert await twitch.fetch_latest_event("https://www.twitch.tv/stepiks_") is None
    assert await youtube.fetch_latest_event("https://www.youtube.com/@omni") is None


def test_creator_alert_service_reports_platform_configuration(tmp_path):
    db = DatabaseManager(f"sqlite:///{tmp_path / 'creator_alerts_config.db'}")
    service = CreatorAlertService(
        CreatorAlertRepository(db),
        ChannelConfigRepository(db),
        _RolePurposeService(),
        {
            CreatorPlatform.TWITCH: _MissingCredentialsClient(),
            CreatorPlatform.YOUTUBE: _NoopClient(),
        },
    )

    assert service.is_platform_configured(CreatorPlatform.TWITCH) is False
    assert service.is_platform_configured(CreatorPlatform.YOUTUBE) is True
    assert service.is_platform_configured(CreatorPlatform.KICK) is False


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
async def test_activity_creator_alert_service_updates_platform_and_restricts_creator_ping_role(tmp_path, monkeypatch):
    db = DatabaseManager(f"sqlite:///{tmp_path / 'activity_creator_alerts_update.db'}")
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
                channel_url="https://example.com/creator",
                channel_name="Creator",
                ping_role_id=999,
            ),
            "token",
        )
        updated = await service.save_source(
            CreatorAlertSourcePayload(
                guild_id=100,
                id=saved["id"],
                platform="youtube",
                channel_url="https://youtube.com/@creator",
                channel_name="Creator",
                ping_role_id=999,
            ),
            "token",
        )

        assert updated["platform"] == "youtube"
        assert updated["ping_role_id"] == "777"
    finally:
        activity_dependencies._db = previous_db
        activity_dependencies._role_purpose_service = previous_role_service
        await db.close()


def test_activity_creator_alert_preview_uses_styled_embed_button_and_spoiler_ping():
    message = build_creator_alert_message(
        CreatorAlertTestPayload(
            guild_id=100,
            platform="youtube",
            channel_name="Creator",
            channel_url="https://youtube.com/watch?v=bhu63w-yd9k",
            ping_role_id=777,
            button_label="Watch live",
        )
    )

    assert message["content"] == "||<@&777>||"
    assert message["embeds"][0]["fields"][0]["value"] == "YouTube"
    assert "прямой эфир на YouTube" in message["embeds"][0]["description"]
    assert message["embeds"][0]["image"]["url"].endswith("bhu63w-yd9k/maxresdefault.jpg")
    assert message["components"][0]["components"][0]["label"] == "Watch live"


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

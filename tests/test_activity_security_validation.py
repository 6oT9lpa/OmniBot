import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.creator_alerts import CreatorAlertSourcePayload
from activity.server.schemas.dev_blog import DevBlogEmbedPayload
from activity.server.schemas.welcome import WelcomeConfigPayload
from core.domain.activity_access import DEFAULT_VISIBLE_MODULES


def test_activity_rejects_empty_or_malformed_bearer_token() -> None:
    for value in ("", "Bearer ", "Bearer token value"):
        with pytest.raises(HTTPException) as error:
            require_bearer_token(value)
        assert error.value.status_code == 401


def test_welcome_schema_rejects_private_images_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WelcomeConfigPayload(guild_id=1, thumbnail_url="https://127.0.0.1/image.png")
    with pytest.raises(ValidationError):
        WelcomeConfigPayload(guild_id=1, unexpected="value")


def test_creator_sources_are_limited_to_the_selected_platform() -> None:
    payload = CreatorAlertSourcePayload(
        guild_id=1,
        platform="twitch",
        channel_url="https://www.twitch.tv/creator",
    )
    assert payload.channel_url == "https://www.twitch.tv/creator"
    with pytest.raises(ValidationError):
        CreatorAlertSourcePayload(guild_id=1, platform="twitch", channel_url="https://example.com/creator")


def test_dev_blog_images_require_public_https_urls() -> None:
    with pytest.raises(ValidationError):
        DevBlogEmbedPayload(description="Text", image_url="http://example.com/image.png")


def test_unassigned_activity_users_only_receive_non_sensitive_modules() -> None:
    assert DEFAULT_VISIBLE_MODULES == ("dashboard", "health")

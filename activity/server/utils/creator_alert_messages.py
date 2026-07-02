from typing import Any

from activity.server.schemas.creator_alerts import CreatorAlertTestPayload
from core.domain.creator_alert import CreatorAlertKind, CreatorContentEvent, CreatorPlatform
from presentation.embeds.creator_alert_embed import CreatorAlertEmbedBuilder


def build_creator_alert_message(payload: CreatorAlertTestPayload) -> dict[str, Any]:
    event = CreatorContentEvent(
        platform=CreatorPlatform(payload.platform),
        alert_kind=CreatorAlertKind(payload.alert_kind),
        event_id="preview",
        creator_name=payload.channel_name,
        title="Preview alert",
        url=payload.channel_url,
        game=payload.game,
        thumbnail_url=_preview_thumbnail_url(payload.channel_url),
    )
    creator_ping = f"||<@&{payload.ping_role_id}>||" if payload.ping_role_id else ""
    embed = CreatorAlertEmbedBuilder.build(
        event,
        title_template=payload.title_template or "",
        description_template=payload.description_template or payload.template or "",
        color=CreatorAlertEmbedBuilder.platform_color(event.platform, payload.color),
        creator_ping=creator_ping,
    ).to_dict()

    message: dict[str, Any] = {
        "content": creator_ping,
        "embeds": [embed],
        "allowed_mentions": {"roles": [str(payload.ping_role_id)] if payload.ping_role_id else []},
    }
    button = _link_button(payload.button_label or "Watch", payload.channel_url)
    if button:
        message["components"] = [{"type": 1, "components": [button]}]
    return message


def _link_button(label: str, url: str) -> dict[str, Any] | None:
    if not url.startswith(("http://", "https://")):
        return None
    return {
        "type": 2,
        "style": 5,
        "label": label[:80] or "Watch",
        "url": url,
    }


def _preview_thumbnail_url(url: str) -> str | None:
    if "youtube.com/watch" in url and "v=" in url:
        video_id = url.split("v=", 1)[1].split("&", 1)[0]
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" if video_id else None
    if "youtu.be/" in url:
        video_id = url.rsplit("/", 1)[-1].split("?", 1)[0]
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" if video_id else None
    if "twitch.tv/" in url:
        login = url.rstrip("/").rsplit("/", 1)[-1]
        return f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{login.lower()}-1280x720.jpg" if login else None
    return None

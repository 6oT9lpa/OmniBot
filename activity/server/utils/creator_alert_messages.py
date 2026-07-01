from typing import Any

from application.utils.creator_alert_templates import CreatorAlertTemplateRenderer
from activity.server.schemas.creator_alerts import CreatorAlertTestPayload
from core.domain.creator_alert import CreatorAlertKind, CreatorContentEvent, CreatorPlatform


def build_creator_alert_message(payload: CreatorAlertTestPayload) -> dict[str, Any]:
    event = CreatorContentEvent(
        platform=CreatorPlatform(payload.platform),
        alert_kind=CreatorAlertKind(payload.alert_kind),
        event_id="preview",
        creator_name=payload.channel_name,
        title="Preview alert",
        url=payload.channel_url,
        game=payload.game,
    )
    title_template = payload.title_template or "{creator.name} is active on {platform}"
    description_template = (
        payload.description_template
        or payload.template
        or "{creator.ping} {creator.name} posted an update: {url}"
    )
    creator_ping = f"<@&{payload.ping_role_id}>" if payload.ping_role_id else ""
    description = CreatorAlertTemplateRenderer.render(
        description_template,
        event,
        creator_ping=creator_ping,
    )
    content = f"<@&{payload.ping_role_id}>" if payload.ping_role_id else ""
    return {
        "content": content,
        "embeds": [
            {
                "title": CreatorAlertTemplateRenderer.render(
                    title_template,
                    event,
                    creator_ping=creator_ping,
                ),
                "description": description,
                "url": payload.channel_url,
                "color": payload.color,
                "fields": [
                    {"name": "Platform", "value": payload.platform.title(), "inline": True},
                    {"name": "Game", "value": payload.game, "inline": True},
                ],
            }
        ],
        "allowed_mentions": {"roles": [str(payload.ping_role_id)] if payload.ping_role_id else []},
    }

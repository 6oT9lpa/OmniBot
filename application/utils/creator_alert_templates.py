from __future__ import annotations

from core.domain.creator_alert import CreatorContentEvent


class CreatorAlertTemplateRenderer:
    @staticmethod
    def render(
        template: str,
        event: CreatorContentEvent,
        *,
        creator_ping: str = "",
    ) -> str:
        values = {
            "creator.name": event.creator_name,
            "creator.ping": creator_ping,
            "platform": event.platform.value.title(),
            "url": event.url,
            "game": event.game or "Just Chatting",
            "title": event.title,
        }
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", value)
        return rendered

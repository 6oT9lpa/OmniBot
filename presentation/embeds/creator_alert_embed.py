from __future__ import annotations

from typing import Optional

import disnake

from application.utils.creator_alert_templates import CreatorAlertTemplateRenderer
from core.domain.creator_alert import CreatorContentEvent, CreatorPlatform


class CreatorAlertEmbedBuilder:
    @staticmethod
    def render_text(
        template: str,
        event: CreatorContentEvent,
        *,
        creator_ping: str = "",
    ) -> str:
        return CreatorAlertTemplateRenderer.render(template, event, creator_ping=creator_ping)

    @staticmethod
    def build(
        event: CreatorContentEvent,
        *,
        title_template: str,
        description_template: str,
        color: int = 0x5865F2,
        creator_ping: str = "",
    ) -> disnake.Embed:
        embed = disnake.Embed(
            title=CreatorAlertEmbedBuilder.render_text(
                title_template,
                event,
                creator_ping=creator_ping,
            )[:256],
            description=CreatorAlertEmbedBuilder.render_text(
                description_template,
                event,
                creator_ping=creator_ping,
            )[:4096],
            url=event.url,
            color=color,
        )
        embed.add_field(name="Platform", value=event.platform.value.title(), inline=True)
        embed.add_field(name="Game", value=event.game or "Not specified", inline=True)
        embed.set_footer(text="Creator Alerts")
        if event.thumbnail_url:
            embed.set_image(url=event.thumbnail_url)
        return embed

    @staticmethod
    def default_stream_embed(event: CreatorContentEvent, *, color: int = 0x5865F2) -> disnake.Embed:
        title_template = "{creator.name} is live on {platform}"
        description_template = "{creator.ping} {title}\nGame: {game}\n{url}"
        return CreatorAlertEmbedBuilder.build(
            event,
            title_template=title_template,
            description_template=description_template,
            color=color,
        )

    @staticmethod
    def platform_color(platform: CreatorPlatform, fallback: Optional[int] = None) -> int:
        if fallback is not None:
            return fallback
        return {
            CreatorPlatform.TWITCH: 0x9146FF,
            CreatorPlatform.YOUTUBE: 0xFF0000,
            CreatorPlatform.KICK: 0x53FC18,
        }.get(platform, 0x5865F2)

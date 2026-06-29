from __future__ import annotations

from typing import Optional

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger
from presentation.views.voice_control.embed_builder import build_voice_control_embed

logger = get_logger(__name__)


async def refresh_voice_control_panel(
    service: VoiceServiceInterface,
    channel: disnake.VoiceChannel,
    owner: disnake.Member,
    admin: Optional[disnake.Member],
) -> None:
    from presentation.views.voice_control.voice_control_view import VoiceControlView

    embed = build_voice_control_embed(owner, admin)
    view = VoiceControlView(service)
    async for message in channel.history(limit=8):
        if message.author == channel.guild.me and message.embeds:
            await message.edit(embed=embed, view=view)
            logger.debug("Voice panel refreshed: channel_id=%s message_id=%s", channel.id, message.id)
            return
    logger.debug("Voice panel refresh skipped: bot panel not found channel_id=%s", channel.id)

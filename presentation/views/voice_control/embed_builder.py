from __future__ import annotations

from typing import Optional

import disnake


def build_voice_control_embed(owner: disnake.Member, admin: Optional[disnake.Member] = None) -> disnake.Embed:
    embed = disnake.Embed(
        title="Управление голосовой комнатой",
        description="Owner остается создателем комнаты. Admin можно взять, снять или передать.",
        color=disnake.Color.blurple(),
    )
    embed.add_field(name="Owner", value=owner.mention, inline=True)
    embed.add_field(name="Admin", value=admin.mention if admin else "Свободно", inline=True)
    embed.set_footer(text="/send опустит эту панель вниз чата")
    return embed

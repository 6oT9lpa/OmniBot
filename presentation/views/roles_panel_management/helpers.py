import disnake

from infrastructure.logging import get_logger

logger = get_logger(__name__)

COLOR_BLUE = 0x5865F2
COLOR_GREEN = 0x57F287
COLOR_RED = 0xED4245
COLOR_ORANGE = 0xFEE75C
COLOR_GREY = 0x99AAB5
MAX_PANEL_ITEMS = 25

COMMON_EMOJIS = ["🎮", "🎨", "🎵", "📚", "💻", "⚽", "🌍", "🔥", "🎭", "✨",
                 "🚀", "🎯", "💎", "🦁", "🐉", "🌸", "🎃", "☕", "🎲", "🏆"]


async def rebuild_panel_embed(
    role_service,
    guild: disnake.Guild,
    panel: dict,
    buttons: list,
) -> disnake.Embed:
    color = panel.get("embed_color", COLOR_GREEN)
    embed = disnake.Embed(
        title=f"{panel.get('embed_title', 'Choose your role')}",
        description=panel.get('embed_description', "Click the button to get or remove a role"),
        color=color,
    )
    visible_buttons = buttons[:MAX_PANEL_ITEMS]
    if visible_buttons:
        lines = []
        for b in visible_buttons:
            emoji = b.get("emoji") or "■"
            lines.append(f"{emoji}  <@&{b['role_id']}>")
        if len(buttons) > MAX_PANEL_ITEMS:
            lines.append(f"...и ещё {len(buttons) - MAX_PANEL_ITEMS}")
        embed.add_field(name="Available roles", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Roles", value="*No roles added yet*", inline=False)
    embed.set_footer(text="Click the button to get or remove a role")
    return embed


def panel_option_label(panel: dict, guild: disnake.Guild) -> str:
    channel = guild.get_channel(panel["channel_id"])
    ch_name = f"#{channel.name}" if channel else "deleted"
    title = panel.get("embed_title") or "Panel"
    return f"{title[:50]} ({ch_name})"

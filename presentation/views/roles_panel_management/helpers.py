from typing import List
import disnake

from infrastructure.logging import get_logger

logger = get_logger(__name__)

COLOR_BLUE = 0x5865F2
COLOR_GREEN = 0x57F287
COLOR_RED = 0xED4245
COLOR_ORANGE = 0xFEE75C
COLOR_GREY = 0x99AAB5
MAX_PANEL_ITEMS = 25


class AdministratorOnlyView(disnake.ui.View):
    """Defence in depth for stateful role-panel management interactions."""

    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        member = interaction.author
        if interaction.guild and isinstance(member, disnake.Member) and member.guild_permissions.administrator:
            return True
        if not interaction.response.is_done():
            await interaction.response.send_message("Only administrators can manage role panels.", ephemeral=True)
        logger.warning("Blocked role-panel management interaction user_id=%s", getattr(member, "id", None))
        return False


def is_safe_self_assignable_role(guild: disnake.Guild, role: disnake.Role | None) -> bool:
    """Self-assignable roles must not grant Discord permissions or be managed."""
    if role is None or role.managed or int(role.permissions.value) != 0:
        return False
    me = guild.me
    return bool(me and me.top_role.position > role.position)

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
        description=panel.get('embed_description', "Нажмите на кнопку ниже, чтобы получить или снять роль"),
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
        embed.add_field(name="Доступные роли", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Roles", value="*No roles added yet*", inline=False)
    embed.set_footer(text="Нажмите на кнопку ниже, чтобы получить или снять роль")
    return embed


def panel_option_label(panel: dict, guild: disnake.Guild) -> str:
    channel = guild.get_channel(panel["channel_id"])
    ch_name = f"#{channel.name}" if channel else "deleted"
    title = panel.get("embed_title") or "Panel"
    return f"{title[:50]} ({ch_name})"


def get_emoji_select_options(guild: disnake.Guild, limit: int = 25) -> List[disnake.SelectOption]:
    """Возвращает список опций для селектора эмодзи: сначала стандартные, затем кастомные."""
    options = []
    for emoji in COMMON_EMOJIS:
        options.append(
            disnake.SelectOption(
                label=emoji,
                value=emoji,
                emoji=emoji
            )
        )

    remaining = limit - len(options)
    if remaining > 0:
        for emoji in guild.emojis[:remaining]:
            emoji_str = str(emoji) 
            options.append(
                disnake.SelectOption(
                    label=emoji.name,
                    value=emoji_str,
                    emoji=emoji_str
                )
            )
            
    return options

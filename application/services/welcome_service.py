import re
from datetime import timezone
from typing import Any, Dict, Optional

import disnake

from core.interfaces.repositories import WelcomeConfigRepositoryInterface
from core.interfaces.services import WelcomeServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class WelcomeService(WelcomeServiceInterface):
    def __init__(self, config_repo: WelcomeConfigRepositoryInterface):
        self._config_repo = config_repo

    async def get_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        return await self._config_repo.get_config(guild_id)

    async def update_config(
        self,
        guild_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        color: Optional[int] = None,
        rules_channel_id: Optional[int] = None,
        roles_channel_id: Optional[int] = None,
    ) -> bool:
        return await self._config_repo.create_or_update(
            guild_id=guild_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            footer_text=footer_text,
            footer_icon_url=footer_icon_url,
            color=color,
            rules_channel_id=rules_channel_id,
            roles_channel_id=roles_channel_id,
        )

    async def set_enabled(self, guild_id: int, is_enabled: bool) -> bool:
        return await self._config_repo.set_enabled(guild_id, is_enabled)

    async def reset_config(self, guild_id: int) -> bool:
        return await self._config_repo.delete_config(guild_id)

    def format_description(
        self,
        description: str,
        member: disnake.Member,
        guild: disnake.Guild,
        rules_channel_id: Optional[int] = None,
        roles_channel_id: Optional[int] = None,
        mention_style: str = "mentions",
    ) -> str:
        result = self.normalize_text(description, member, guild, mention_style=mention_style)

        if rules_channel_id:
            channel = guild.get_channel(rules_channel_id)
            result = result.replace("{rules}", channel.mention if channel else "#правила")
        else:
            result = result.replace("{rules}", "#правила")

        if roles_channel_id:
            channel = guild.get_channel(roles_channel_id)
            result = result.replace("{roles}", channel.mention if channel else "#роли")
        else:
            result = result.replace("{roles}", "#роли")

        return result

    def normalize_text(
        self,
        value: str,
        member: disnake.Member,
        guild: disnake.Guild,
        *,
        mention_style: str = "mentions",
    ) -> str:
        if not value:
            return ""

        joined_at = member.joined_at
        if joined_at and joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=timezone.utc)
        joined_text = joined_at.strftime("%d.%m.%Y %H:%M") if joined_at else ""

        replacements = {
            "{user}": member.display_name,
            "{user_name}": str(member),
            "{server}": guild.name,
            "{guild}": guild.name,
            "{member_count}": str(guild.member_count or 0),
            "{joined_at}": joined_text,
        }
        result = value
        for placeholder, replacement in replacements.items():
            result = result.replace(placeholder, replacement)

        result = re.sub(
            r"\{channel\.(\d{15,25})\}",
            lambda match: self._format_channel_placeholder(guild, int(match.group(1)), mention_style),
            result,
        )
        result = re.sub(
            r"\{role\.(\d{15,25})\}",
            lambda match: self._format_role_placeholder(guild, int(match.group(1)), mention_style),
            result,
        )
        result = re.sub(
            r"\{user\.(\d{15,25})\}",
            lambda match: self._format_user_placeholder(guild, int(match.group(1)), mention_style),
            result,
        )
        logger.debug("Welcome text normalized guild_id=%s member_id=%s", guild.id, member.id)
        return result

    def _format_channel_placeholder(self, guild: disnake.Guild, channel_id: int, mention_style: str) -> str:
        return f"<#{channel_id}>"

    def _format_role_placeholder(self, guild: disnake.Guild, role_id: int, mention_style: str) -> str:
        if mention_style == "plain":
            role = guild.get_role(role_id)
            return f"@{role.name}" if role else f"@{role_id}"
        return f"<@&{role_id}>"

    def _format_user_placeholder(self, guild: disnake.Guild, user_id: int, mention_style: str) -> str:
        return f"<@{user_id}>"

    def build_embed(
        self,
        member: disnake.Member,
        config: Optional[Dict[str, Any]] = None,
    ) -> disnake.Embed:
        guild = member.guild

        is_enabled = config.get("is_enabled") if config else None
        if config is None or is_enabled == 0:
            return self._build_default_embed(member)

        title = config.get("title") or "Добро пожаловать!"
        description = config.get("description") or ""
        color = config.get("color") or 0x57F287
        thumbnail_url = config.get("thumbnail_url")
        footer_text = config.get("footer_text")
        footer_icon_url = config.get("footer_icon_url")
        rules_channel_id = config.get("rules_channel_id")
        roles_channel_id = config.get("roles_channel_id")
        title = self.normalize_text(title, member, guild, mention_style="plain")
        footer_text = self.normalize_text(footer_text or "", member, guild, mention_style="plain")

        formatted_description = self.format_description(
            description, member, guild, rules_channel_id, roles_channel_id, mention_style="plain"
        )

        embed = disnake.Embed(
            title=title,
            description=formatted_description,
            color=color,
        )

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        elif guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        if footer_text:
            embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        else:
            embed.set_footer(
                text=guild.name,
                icon_url=guild.icon.url if guild.icon else None,
            )

        return embed

    def _build_default_embed(self, member: disnake.Member) -> disnake.Embed:
        guild = member.guild
        embed = disnake.Embed(
            title=f"Добро пожаловать на {guild.name}!",
            description=(
                f"Привет, {member.mention}! Рады видеть тебя на нашем сервере.\n\n"
                "**Перед тем как начать:**\n"
                "• Ознакомься с правилами сервера\n"
                "• Выбери интересующие тебя роли\n"
                "• Представься в соответствующем канале\n\n"
                "Если возникнут вопросы — обращайся к модераторам."
            ),
            color=0x57F287,
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(
            text=guild.name,
            icon_url=guild.icon.url if guild.icon else None,
        )
        return embed

    async def get_welcome_buttons(self, guild: disnake.Guild):
        from presentation.cogs.member_events.welcome_buttons_view import WelcomeButtonsView

        config = await self.get_config(guild.id)
        rules_channel_id = config.get("rules_channel_id") if config else None
        roles_channel_id = config.get("roles_channel_id") if config else None

        rules_url = None
        roles_url = None

        if rules_channel_id:
            ch = guild.get_channel(rules_channel_id)
            if ch:
                rules_url = f"https://discord.com/channels/{guild.id}/{ch.id}"

        if roles_channel_id:
            ch = guild.get_channel(roles_channel_id)
            if ch:
                roles_url = f"https://discord.com/channels/{guild.id}/{ch.id}"

        return WelcomeButtonsView(rules_url=rules_url, roles_url=roles_url)

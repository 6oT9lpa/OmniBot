from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from typing import Union, Optional

import disnake

from presentation.embeds import EmbedBuilder


def format_date(dt: datetime) -> str:
    MSK = ZoneInfo("Europe/Moscow")
    return dt.astimezone(MSK).strftime("%H:%M %d.%m.%Y")


def format_duration_seconds(seconds: Optional[int]) -> str:
    if not seconds or seconds <= 0:
        return "Permanent"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return format_date(expires_at)


class ModerationBanEmbedBuilder:
    @staticmethod
    def build_ban(
        moderator: disnake.Member,
        target: disnake.Member,
        duration_seconds: Optional[int] = None,
        delete_message_days: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        builder = EmbedBuilder(color=0xED4245)

        builder.set_author(
            name=f"{moderator} (ID: {moderator.id})",
            icon_url=moderator.display_avatar.url,
        )

        builder.set_thumbnail(url=target.display_avatar.url)
        builder.set_description("__** Action: 🔨 User Banned **__")
        builder.add_field(
            "👤 User",
            f"> {target.mention}\n> `{target} (ID: {target.id})`",
            inline=False,
        )

        if duration_seconds and duration_seconds > 0:
            builder.add_field(
                "⏳ Duration",
                f"> `{format_duration_seconds(duration_seconds)}`",
                inline=True,
            )
        else:
            builder.add_field(
                "⏳ Duration",
                "`Permanent`",
                inline=True,
            )

        if delete_message_days is not None:
            builder.add_field(
                "🗑️ Deleted Messages",
                f"> `{delete_message_days} day(s)`",
                inline=True,
            )

        builder.add_field(
            "📋 Reason",
            f"> {reason or 'No reason provided'}",
            inline=False,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        builder.set_footer(text=f"User ID: {target.id}  •  {format_date(timestamp)}")

        return builder.build()

    @staticmethod
    def build_unban(
        moderator: disnake.Member,
        target: disnake.Member,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        builder = EmbedBuilder(color=0x57F287)

        builder.set_author(
            name=f"{moderator}",
            icon_url=moderator.display_avatar.url,
        )

        builder.set_description("__**Action: 🔓 User Unbanned**__")

        builder.add_field(
            "👤 User",
            f"> `ID: {target.id}`",
            inline=False,
        )

        builder.add_field(
            "📋 Reason",
            f"> {reason or 'No reason provided'}",
            inline=False,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        builder.set_footer(text=f"User ID: {target.id}  •  {format_date(timestamp)}")

        return builder.build()


class ModerationWarnEmbedBuilder:
    @staticmethod
    def build_warn(
        moderator: Union[disnake.User, disnake.Member],
        target: Union[disnake.User, disnake.Member],
        duration_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        builder = EmbedBuilder(color=0xFEE75C)

        builder.set_author(
            name=f"{moderator}",
            icon_url=moderator.display_avatar.url,
        )
        builder.set_thumbnail(url=target.display_avatar.url)
        builder.set_description("__**Action: ⚠️ User Warned**__")

        builder.add_field(
            "👤 User",
            f"> {target.mention}\n> `{target} ({target.id})`",
            inline=False,
        )
        builder.add_field(
            "⏳ Duration",
            f"> `{format_duration_seconds(duration_seconds)}`",
            inline=True,
        )
        builder.add_field(
            "📋 Reason",
            f"> {reason or 'No reason provided'}",
            inline=False,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        builder.set_footer(text=f"User ID: {target.id}  •  {format_date(timestamp)}")

        return builder.build()


class ModerationKickEmbedBuilder:
    @staticmethod
    def build_kick(
        moderator: Union[disnake.User, disnake.Member],
        target: Union[disnake.User, disnake.Member],
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        builder = EmbedBuilder(color=0xED4245)

        builder.set_author(
            name=f"{moderator}",
            icon_url=moderator.display_avatar.url,
        )
        builder.set_thumbnail(url=target.display_avatar.url)
        builder.set_description("__**Action: 👢 User Kicked**__")

        builder.add_field(
            "👤 User",
            f"> {target.mention}\n> `{target} ({target.id})`",
            inline=False,
        )
        builder.add_field(
            "📋 Reason",
            f"> {reason or 'No reason provided'}",
            inline=False,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        builder.set_footer(text=f"User ID: {target.id}  •  {format_date(timestamp)}")

        return builder.build()


class ModerationMuteEmbedBuilder:
    @staticmethod
    def build_mute(
        moderator: Union[disnake.User, disnake.Member],
        target: Union[disnake.User, disnake.Member],
        duration_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        builder = EmbedBuilder(color=0x5865F2)

        builder.set_author(
            name=f"{moderator}",
            icon_url=moderator.display_avatar.url,
        )
        builder.set_thumbnail(url=target.display_avatar.url)
        builder.set_description("__**Action: 🔇 User Muted**__")

        builder.add_field(
            "👤 User",
            f"> {target.mention}\n> `{target} ({target.id})`",
            inline=False,
        )
        builder.add_field(
            "⏳ Duration",
            f"> `{format_duration_seconds(duration_seconds)}`",
            inline=True,
        )
        builder.add_field(
            "📋 Reason",
            f"> {reason or 'No reason provided'}",
            inline=False,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        builder.set_footer(text=f"User ID: {target.id}  •  {format_date(timestamp)}")

        return builder.build()

    @staticmethod
    def build_unmute(
        moderator: Union[disnake.User, disnake.Member],
        target: Union[disnake.User, disnake.Member],
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        builder = EmbedBuilder(color=0x57F287)

        builder.set_author(
            name=f"{moderator}",
            icon_url=moderator.display_avatar.url,
        )
        builder.set_thumbnail(url=target.display_avatar.url)
        builder.set_description("__**Action: 🔊 User Unmuted**__")

        builder.add_field(
            "👤 User",
            f"> {target.mention}\n> `{target} ({target.id})`",
            inline=False,
        )
        builder.add_field(
            "📋 Reason",
            f"> {reason or 'No reason provided'}",
            inline=False,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        builder.set_footer(text=f"User ID: {target.id}  •  {format_date(timestamp)}")
        
        return builder.build()
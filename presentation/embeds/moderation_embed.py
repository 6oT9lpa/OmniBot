from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo

import disnake

from presentation.embeds import EmbedBuilder


DiscordUser = Union[disnake.User, disnake.Member]


def format_date(dt: datetime) -> str:
    msk = ZoneInfo("Europe/Moscow")
    return dt.astimezone(msk).strftime("%d.%m.%Y")


def format_duration_seconds(seconds: Optional[int]) -> str:
    if not seconds or seconds <= 0:
        return "Permanent"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return f"until {format_date(expires_at)}"


def _title(user: DiscordUser) -> str:
    return f"{user} ({user.id})"


def _mention(user: DiscordUser) -> str:
    return getattr(user, "mention", str(user))


def _avatar_url(user: DiscordUser) -> Optional[str]:
    avatar = getattr(user, "display_avatar", None)
    return getattr(avatar, "url", None)


def _build_embed(
    *,
    target: DiscordUser,
    color: int,
    action: str,
    user_field: str,
    moderator: Optional[DiscordUser] = None,
    duration_seconds: Optional[int] = None,
    include_duration: bool = False,
    delete_message_days: Optional[int] = None,
    reason: Optional[str] = None,
) -> disnake.Embed:
    builder = EmbedBuilder(color=color)
    builder.set_title(_title(target))
    if moderator:
        builder.set_author(name=_title(moderator), icon_url=_avatar_url(moderator))
    if _avatar_url(target):
        builder.set_thumbnail(url=_avatar_url(target))

    builder.set_description(action)
    builder.add_field(user_field, _mention(target), inline=False)

    if include_duration or duration_seconds:
        builder.add_field("Duration:", format_duration_seconds(duration_seconds), inline=True)
    if delete_message_days is not None:
        builder.add_field("Delete Message:", f"{delete_message_days} day(s)", inline=True)
    if reason:
        builder.add_field("Reason:", reason, inline=False)

    builder.set_footer(text=f"User ID: {target.id} | {format_date(datetime.now(timezone.utc))}")
    return builder.build()


class ModerationBanEmbedBuilder:
    @staticmethod
    def build_ban(
        moderator: DiscordUser,
        target: Optional[DiscordUser] = None,
        duration_seconds: Optional[int] = None,
        delete_message_days: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        actual_target = target or moderator
        return _build_embed(
            target=actual_target,
            moderator=moderator if target else None,
            color=0xED4245,
            action="User banned",
            user_field="Banned User:",
            duration_seconds=duration_seconds,
            include_duration=target is not None,
            delete_message_days=delete_message_days,
            reason=reason,
        )

    @staticmethod
    def build_unban(
        moderator: DiscordUser,
        target: Optional[DiscordUser] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        actual_target = target or moderator
        builder = EmbedBuilder(color=0x57F287)
        builder.set_title(f"User unbanned (ID: {actual_target.id})")
        if target:
            builder.set_author(name=_title(moderator), icon_url=_avatar_url(moderator))
        builder.set_description("User unbanned")
        builder.add_field("User ID:", str(actual_target.id), inline=False)
        if reason:
            builder.add_field("Reason:", reason, inline=False)
        builder.set_footer(text=f"User ID: {actual_target.id} | {format_date(datetime.now(timezone.utc))}")
        return builder.build()


class ModerationWarnEmbedBuilder:
    @staticmethod
    def build_warn(
        moderator: DiscordUser,
        target: Optional[DiscordUser] = None,
        duration_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        actual_target = target or moderator
        return _build_embed(
            target=actual_target,
            moderator=moderator if target else None,
            color=0xFEE75C,
            action="User warned",
            user_field="Warned User:",
            duration_seconds=duration_seconds,
            include_duration=duration_seconds is not None,
            reason=reason,
        )

    @staticmethod
    def build_unwarn(target: DiscordUser, reason: Optional[str] = None) -> disnake.Embed:
        return _build_embed(
            target=target,
            color=0x57F287,
            action="User unwarned",
            user_field="Unwarned User:",
            reason=reason,
        )


class ModerationKickEmbedBuilder:
    @staticmethod
    def build_kick(
        moderator: DiscordUser,
        target: Optional[DiscordUser] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        actual_target = target or moderator
        return _build_embed(
            target=actual_target,
            moderator=moderator if target else None,
            color=0xED4245,
            action="User kicked",
            user_field="Kicked User:",
            reason=reason,
        )


class ModerationMuteEmbedBuilder:
    @staticmethod
    def build_mute(
        moderator: DiscordUser,
        target: Optional[DiscordUser] = None,
        duration_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        actual_target = target or moderator
        return _build_embed(
            target=actual_target,
            moderator=moderator if target else None,
            color=0x5865F2,
            action="User muted",
            user_field="Muted User:",
            duration_seconds=duration_seconds,
            include_duration=duration_seconds is not None,
            reason=reason,
        )

    @staticmethod
    def build_unmute(
        moderator: DiscordUser,
        target: Optional[DiscordUser] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        actual_target = target or moderator
        return _build_embed(
            target=actual_target,
            moderator=moderator if target else None,
            color=0x57F287,
            action="User unmuted",
            user_field="Unmuted User:",
            reason=reason,
        )


class ModerationTimeoutEmbedBuilder:
    @staticmethod
    def build_timeout(
        target: DiscordUser,
        duration_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> disnake.Embed:
        return _build_embed(
            target=target,
            color=0x5865F2,
            action="User timed out",
            user_field="Timed out User:",
            duration_seconds=duration_seconds,
            include_duration=duration_seconds is not None,
            reason=reason,
        )

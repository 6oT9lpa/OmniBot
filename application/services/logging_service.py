from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Union

import disnake

from application.dto.logging_dto import MessageLogDTO, GuildEventLogDTO
from core.domain.value_objects import EventType, PunishmentType
from core.interfaces.repositories import GuildEventLogRepositoryInterface, MessageLogRepositoryInterface
from core.interfaces.services import AuditLogServiceInterface, LoggingServiceInterface
from infrastructure.config import BotConfig
from infrastructure.logging import get_logger
from presentation.embeds.panel_management.moderation import (
    ModerationBanEmbedBuilder,
    ModerationWarnEmbedBuilder,
    ModerationKickEmbedBuilder,
    ModerationMuteEmbedBuilder,
)
from presentation.embeds.panel_management.logging import (
    VoiceLogEmbedBuilder,
    MessageLogEmbedBuilder,
)

logger = get_logger(__name__)


class LoggingService(LoggingServiceInterface):
    def __init__(
        self,
        message_repo: MessageLogRepositoryInterface,
        guild_event_repo: GuildEventLogRepositoryInterface,
        audit_log_service: AuditLogServiceInterface,
        config: BotConfig,
    ):
        self._message_repo = message_repo
        self._guild_event_repo = guild_event_repo
        self._audit_log_service = audit_log_service
        self._config = config
        self._bot: Optional[disnake.Client] = None

    def set_bot(self, bot: disnake.Client) -> None:
        self._bot = bot

    async def log_message(
        self,
        message: disnake.Message,
        *,
        ai_flagged: bool = False,
        ai_reason: Optional[str] = None,
    ) -> None:
        if not getattr(message, "guild", None):
            return
        details = {"ai_flagged": ai_flagged, "ai_reason": ai_reason} if ai_reason else None
        await self._persist_and_send(
            guild_id=message.guild.id,
            event_type="message",
            channel_id=message.channel.id,
            actor_id=message.author.id,
            actor_name=str(message.author),
            target_id=message.id,
            details=details,
        )
        await self._message_repo.add(
            MessageLogDTO(
                guild_id=message.guild.id,
                message_id=message.id,
                author_id=message.author.id,
                author_name=str(message.author),
                channel_id=message.channel.id,
                content=message.content or "",
                created_at=datetime.now(timezone.utc),
                event_type="message",
                ai_flagged=ai_flagged,
                retention_until=self._retention_until(),
            )
        )

    async def log_message_edit(
        self,
        before: disnake.Message,
        after: disnake.Message,
    ) -> None:
        if not getattr(after, "guild", None) or not getattr(before, "guild", None) or before.author.bot:
            return
        if not before.content and not after.content:
            return
        embed = MessageLogEmbedBuilder.build_edit(after.author)
        await self._persist_and_send(
            guild_id=after.guild.id,
            event_type="message_edit",
            channel_id=after.channel.id,
            actor_id=after.author.id,
            actor_name=str(after.author),
            target_id=after.id,
            details={"before": before.content, "after": after.content},
            embed=embed,
        )
        await self._message_repo.add(
            MessageLogDTO(
                guild_id=after.guild.id,
                message_id=after.id,
                author_id=after.author.id,
                author_name=str(after.author),
                channel_id=after.channel.id,
                content=f"Before: {before.content}\nAfter: {after.content}",
                created_at=datetime.now(timezone.utc),
                event_type="message_edit",
                is_edited=True,
                retention_until=self._retention_until(),
            )
        )

    async def log_message_delete(
        self,
        message: disnake.Message,
        *,
        deleted_by: Optional[disnake.Member] = None,
    ) -> None:
        if not getattr(message, "guild", None):
            return
        embed = MessageLogEmbedBuilder.build_delete(message.author)
        await self._persist_and_send(
            guild_id=message.guild.id,
            event_type="message_delete",
            channel_id=message.channel.id,
            actor_id=message.author.id,
            actor_name=str(message.author),
            target_id=message.id,
            target_name=str(message.author),
            details={"content": message.content},
            embed=embed,
        )
        await self._message_repo.add(
            MessageLogDTO(
                guild_id=message.guild.id,
                message_id=message.id,
                author_id=message.author.id,
                author_name=str(message.author),
                channel_id=message.channel.id,
                content=message.content or "",
                created_at=datetime.now(timezone.utc),
                event_type="message_delete",
                is_deleted=True,
                retention_until=self._retention_until(),
            )
        )

    async def log_bulk_delete(
        self,
        messages: List[disnake.Message],
        channel: disnake.TextChannel,
        deleted_by: Optional[disnake.Member] = None,
    ) -> None:
        if not getattr(channel, "guild", None):
            return
        await self._persist_and_send(
            guild_id=channel.guild.id,
            event_type="message_delete_bulk",
            channel_id=channel.id,
            actor_id=deleted_by.id if deleted_by else None,
            actor_name=str(deleted_by) if deleted_by else None,
            details={"message_count": len(messages)},
        )
        for message in messages:
            await self._message_repo.add(
                MessageLogDTO(
                    guild_id=channel.guild.id,
                    message_id=message.id,
                    author_id=message.author.id,
                    author_name=str(message.author),
                    channel_id=channel.id,
                    content=message.content or "",
                    created_at=datetime.now(timezone.utc),
                    event_type="message_delete_bulk",
                    is_deleted=True,
                    retention_until=self._retention_until(),
                )
            )

    async def log_channel_event(
        self,
        event_type: EventType,
        channel: Union[disnake.TextChannel, disnake.VoiceChannel],
        *,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        await self._persist_and_send(
            guild_id=channel.guild.id,
            event_type=event_type.value,
            channel_id=channel.id,
            target_id=channel.id,
            target_name=channel.name,
            details=extra_data,
        )

    async def log_role_event(
        self,
        event_type: EventType,
        role: disnake.Role,
        *,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        await self._persist_and_send(
            guild_id=role.guild.id,
            event_type=event_type.value,
            target_id=role.id,
            target_name=role.name,
            details=extra_data,
        )

    async def log_voice_event(
        self,
        member: disnake.Member,
        before: Optional[disnake.VoiceState],
        after: Optional[disnake.VoiceState],
    ) -> None:
        if before and before.channel and after and after.channel:
            embed = VoiceLogEmbedBuilder.build_move(member, before.channel.name, after.channel.name)
            await self._persist_and_send(
                guild_id=member.guild.id,
                event_type=EventType.VOICE_MOVE.value,
                actor_id=member.id,
                actor_name=str(member),
                target_id=member.id,
                target_name=str(member),
                details={"before_channel": before.channel.name, "after_channel": after.channel.name},
                embed=embed,
            )
        elif before and before.channel:
            embed = VoiceLogEmbedBuilder.build_leave(member, before.channel.name)
            await self._persist_and_send(
                guild_id=member.guild.id,
                event_type=EventType.VOICE_LEAVE.value,
                actor_id=member.id,
                actor_name=str(member),
                target_id=member.id,
                target_name=str(member),
                details={"channel": before.channel.name},
                embed=embed,
            )
        elif after and after.channel:
            embed = VoiceLogEmbedBuilder.build_join(member, after.channel.name)
            await self._persist_and_send(
                guild_id=member.guild.id,
                event_type=EventType.VOICE_JOIN.value,
                actor_id=member.id,
                actor_name=str(member),
                target_id=member.id,
                target_name=str(member),
                details={"channel": after.channel.name},
                embed=embed,
            )

    async def log_moderation_action(
        self,
        action_type: PunishmentType,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        duration: Optional[int] = None,
        punishment_id: Optional[int] = None,
    ) -> None:
        embed = self._build_moderation_embed(action_type, moderator, target, reason, duration)
        await self._persist_and_send(
            guild_id=moderator.guild.id,
            event_type=f"moderation_{action_type.value}",
            actor_id=moderator.id,
            actor_name=str(moderator),
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason, "duration_seconds": duration, "punishment_id": punishment_id},
            embed=embed,
        )

    async def log_audit_mute(self, target: disnake.Member, duration_seconds: int, reason: str) -> None:
        embed = ModerationMuteEmbedBuilder.build_mute(target, duration_seconds, reason)
        await self._persist_and_send(
            guild_id=target.guild.id,
            event_type="moderation_audit_mute",
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason, "duration_seconds": duration_seconds},
            embed=embed,
        )

    async def log_audit_unmute(self, target: disnake.Member, duration_seconds: int, reason: str) -> None:
        embed = ModerationMuteEmbedBuilder.build_mute(target, duration_seconds, reason)
        await self._persist_and_send(
            guild_id=target.guild.id,
            event_type="moderation_audit_unmute",
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason},
            embed=embed,
        )

    async def log_audit_ban(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        guild_id: Optional[int] = None, 
    ) -> None:
        embed = ModerationBanEmbedBuilder.build_ban(moderator=moderator, target=target, reason=reason)
        resolved_guild_id = target.guild.id if isinstance(target, disnake.Member) else guild_id
        await self._persist_and_send(
            guild_id=resolved_guild_id,
            event_type="moderation_audit_ban",
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason},
            embed=embed,
        )
    
    async def log_audit_unban(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        guild_id: Optional[int] = None, 
    ) -> None:
        embed = ModerationBanEmbedBuilder.build_unban(moderator=moderator, target=target, reason=reason)
        resolved_guild_id = target.guild.id if isinstance(target, disnake.Member) else guild_id
        await self._persist_and_send(
            guild_id=resolved_guild_id,
            event_type="moderation_audit_unban",
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason},
            embed=embed,
        )

    async def log_audit_kick(self, target: disnake.Member, reason: str) -> None:
        embed = ModerationKickEmbedBuilder.build_kick(target, reason)
        await self._persist_and_send(
            guild_id=target.guild.id,
            event_type="moderation_audit_kick",
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason},
            embed=embed,
        )

    async def cleanup_expired(self) -> None:
        cutoff = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._message_repo.cleanup_expired(cutoff)
        await self._guild_event_repo.cleanup_expired(cutoff)

    async def _persist_and_send(
        self,
        *,
        guild_id: Optional[int],
        event_type: str,
        channel_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        embed: Optional[disnake.Embed] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._guild_event_repo.add(
            GuildEventLogDTO(
                guild_id=guild_id,
                channel_id=channel_id,
                actor_id=actor_id,
                actor_name=actor_name,
                target_id=target_id,
                target_name=target_name,
                event_type=event_type,
                details=str(details) if details else None,
                created_at=now,
                retention_until=self._retention_until(),
            )
        )
        if embed is None:
            embed = self._build_embed(event_type, actor_name, target_name, details)
        if guild_id is not None:
            await self._audit_log_service.send_to_log_channel(guild_id, embed, channel_id=channel_id)

    def _build_moderation_embed(
        self,
        action_type: PunishmentType,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        duration: Optional[int],
    ) -> disnake.Embed:
        if action_type == PunishmentType.BAN:
            return ModerationBanEmbedBuilder.build_ban(moderator=moderator, target=target, duration_seconds=duration, reason=reason)
        elif action_type == PunishmentType.UNBAN:
            return ModerationBanEmbedBuilder.build_unban(moderator=moderator, target=target, reason=reason)
        elif action_type == PunishmentType.WARN:
            return ModerationWarnEmbedBuilder.build_warn(moderator=moderator, target=target, duration_seconds=duration, reason=reason)
        elif action_type == PunishmentType.KICK:
            return ModerationKickEmbedBuilder.build_kick(moderator=moderator, target=target, reason=reason)
        elif action_type == PunishmentType.MUTE:
            return ModerationMuteEmbedBuilder.build_mute(moderator=moderator, duration_seconds=duration, target=target, reason=reason)
        elif action_type == PunishmentType.UNMUTE:
            return ModerationMuteEmbedBuilder.build_unmute(moderator=moderator, target=target, reason=reason)
        return disnake.Embed(title=f"{target} ({target.id})", color=0x5865F2)

    def _build_embed(
        self,
        event_type: str,
        actor_name: Optional[str],
        target_name: Optional[str],
        details: Optional[Dict[str, Any]],
    ) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"Событие: {event_type}",
            description=self._format_details(details),
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc),
        )
        if actor_name:
            embed.add_field(name="Исполнитель", value=actor_name, inline=True)
        if target_name:
            embed.add_field(name="Цель", value=target_name, inline=True)
        return embed

    def _format_details(self, details: Optional[Dict[str, Any]]) -> str:
        if not details:
            return "—"
        lines = []
        for key, value in details.items():
            text = str(value)
            if len(text) > 900:
                text = text[:900] + "..."
            lines.append(f"**{key}**: {text}")
        return "\n".join(lines)

    def _retention_until(self) -> datetime:
        """Единый метод для расчёта срока хранения событий и сообщений."""

        return datetime.now(timezone.utc).replace(microsecond=0) + timedelta(
            days=self._config.message_log_retention_days
        )
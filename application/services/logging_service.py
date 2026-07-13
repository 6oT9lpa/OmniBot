import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Union

import disnake

from application.dto.logging_dto import MessageLogDTO, GuildEventLogDTO
from core.domain.value_objects import EventType, PunishmentType
from core.interfaces.repositories import GuildEventLogRepositoryInterface, MessageLogRepositoryInterface
from core.interfaces.services import AuditLogServiceInterface, LoggingServiceInterface
from infrastructure.config import BotConfig
from infrastructure.database.connection import DatabaseManager
from infrastructure.logging import get_logger
from presentation.embeds import (
    ModerationBanEmbedBuilder,
    ModerationWarnEmbedBuilder,
    ModerationKickEmbedBuilder,
    ModerationMuteEmbedBuilder,
    ChannelLogEmbedBuilder,
    ChannelCreateEmbedBuilder,
    ChannelDeleteEmbedBuilder,
    MessageEditLogEmbedBuilder,
    MessageDeleteLogEmbedBuilder,
    VoiceLogEmbedBuilder,
    BulkDeleteEmbedBuilder,
    RoleCreateEmbedBuilder,
    RoleDeleteEmbedBuilder,
    RoleUpdateEmbedBuilder,
    MemberRoleUpdateEmbedBuilder,
    MemberEventEmbedBuilder,
    VoiceOwnerTransferEmbedBuilder,
)

logger = get_logger(__name__)


class LoggingService(LoggingServiceInterface):
    def __init__(
        self,
        message_repo: MessageLogRepositoryInterface,
        guild_event_repo: GuildEventLogRepositoryInterface,
        audit_log_service: AuditLogServiceInterface,
        config: BotConfig,
        database_manager: Optional[DatabaseManager] = None,
    ):
        self._message_repo = message_repo
        self._guild_event_repo = guild_event_repo
        self._audit_log_service = audit_log_service
        self._config = config
        self._database_manager = database_manager
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
            source_channel_id=message.channel.id,
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

        logger.debug("Logged message id=%s from user=%s", message.id, message.author.id)

    async def log_message_edit(
        self,
        before: disnake.Message,
        after: disnake.Message,
    ) -> None:
        if not getattr(after, "guild", None) or not getattr(before, "guild", None) or before.author.bot:
            return
        
        if not before.content and not after.content:
            return

        embed = MessageEditLogEmbedBuilder.build_edit(
            after,
            before.content or "",
            after.content or "",
            datetime.now(timezone.utc),
        )

        await self._persist_and_send(
            guild_id=after.guild.id,
            event_type="message_edit",
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

        logger.debug("Logged message edit id=%s by user=%s", after.id, after.author.id)

    async def log_message_delete(
        self,
        message: disnake.Message,
        *,
        deleted_by: Optional[disnake.Member] = None,
    ) -> None:
        if not getattr(message, "guild", None):
            return
        
        embed = MessageDeleteLogEmbedBuilder.build_delete(
            message,
            deleted_by,
            datetime.now(timezone.utc),
        )

        await self._persist_and_send(
            guild_id=message.guild.id,
            event_type="message_delete",
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

        logger.debug("Logged message delete id=%s by user=%s", message.id, deleted_by.id if deleted_by else "unknown")

    async def log_bulk_delete(
        self,
        messages: List[disnake.Message],
        channel: disnake.TextChannel,
        deleted_by: Optional[disnake.Member] = None,
    ) -> None:
        if not getattr(channel, "guild", None):
            return

        embed = BulkDeleteEmbedBuilder.build_bulk_delete(channel, len(messages), deleted_by, datetime.now(timezone.utc))
        
        await self._persist_and_send(
            guild_id=channel.guild.id,
            event_type="message_delete_bulk",
            source_channel_id=channel.id,
            actor_id=deleted_by.id if deleted_by else None,
            actor_name=str(deleted_by) if deleted_by else None,
            embed=embed,
        )
        
        for message in messages:
            if not message or not hasattr(message, 'id'):
                logger.warning("Skipping invalid message object in bulk delete: %s", message)
                continue

            try:
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
            except Exception as e:
                logger.error("Failed to save message %s to log: %s", message.id, e)
        
        logger.info("Logged bulk delete of %d messages in channel %s by %s", len(messages), channel.id, deleted_by.id if deleted_by else "unknown")

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
            target_id=channel.id,
            target_name=channel.name,
            details=extra_data,
        )

        logger.debug("Logged channel event %s for channel %s", event_type.value, channel.id)

    async def log_role_create(
        self,
        role: disnake.Role,
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        embed = RoleCreateEmbedBuilder.build_create(role, moderator, timestamp or datetime.now(timezone.utc))
        await self._persist_and_send(
            guild_id=role.guild.id,
            event_type="role_create",
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=role.id,
            target_name=role.name,
            details={"role": {"id": role.id, "name": role.name}},
            embed=embed,
        )
        logger.info("Logged role create for role %s", role.id)

    async def log_role_delete(
        self,
        role: disnake.Role,
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        embed = RoleDeleteEmbedBuilder.build_delete(role, moderator, timestamp or datetime.now(timezone.utc))
        await self._persist_and_send(
            guild_id=role.guild.id,
            event_type="role_delete",
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=role.id,
            target_name=role.name,
            details={"role": {"id": role.id, "name": role.name}},
            embed=embed,
        )
        logger.info("Logged role delete for role %s", role.id)

    async def log_role_update(
        self,
        before: disnake.Role,
        after: disnake.Role,
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        changes = self._detect_role_changes(before, after)
        embed = RoleUpdateEmbedBuilder.build_update(before, after, changes, moderator, timestamp or datetime.now(timezone.utc))
        await self._persist_and_send(
            guild_id=after.guild.id,
            event_type="role_update",
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=after.id,
            target_name=after.name,
            details={"changes": changes},
            embed=embed,
        )
        logger.info("Logged role update for role %s, changes: %s", after.id, changes)

    async def log_member_role_update(
        self,
        member: disnake.Member,
        before_roles: List[disnake.Role],
        after_roles: List[disnake.Role],
        moderator: Optional[Union[disnake.Member, disnake.User]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        # Сравниваем списки ролей
        added = [r for r in after_roles if r not in before_roles]
        removed = [r for r in before_roles if r not in after_roles]
        if not added and not removed:
            return
        embed = MemberRoleUpdateEmbedBuilder.build_update(member, added, removed, moderator, timestamp or datetime.now(timezone.utc))
        await self._persist_and_send(
            guild_id=member.guild.id,
            event_type="member_role_update",
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=member.id,
            target_name=str(member),
            details={
                "added_roles": [{"id": role.id, "name": role.name} for role in added],
                "removed_roles": [{"id": role.id, "name": role.name} for role in removed],
            },
            embed=embed,
        )
        logger.info("Logged member role update for %s, added: %s, removed: %s", member.id, [r.id for r in added], [r.id for r in removed])

    async def log_member_event(
        self,
        event_type: EventType,
        member: disnake.Member,
        *,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if event_type == EventType.MEMBER_JOIN:
            logger.debug("Skipping generic member_join log for member %s", member.id)
            return
        embed = self._build_member_event_embed(event_type, member, extra_data)
        await self._persist_and_send(
            guild_id=member.guild.id,
            event_type=event_type.value,
            actor_id=member.id,
            actor_name=str(member),
            target_id=member.id,
            target_name=str(member),
            details=extra_data,
            embed=embed,
        )
        logger.info("Logged member event %s for member %s", event_type.value, member.id)

    async def log_voice_event(
        self,
        member: disnake.Member,
        before: Optional[disnake.VoiceState],
        after: Optional[disnake.VoiceState],
    ) -> None:
        
        timestamp = datetime.now(timezone.utc)
        before_channel = before.channel if before else None
        after_channel = after.channel if after else None

        if before_channel == after_channel:
            return

        if before_channel and after_channel:
            embed = VoiceLogEmbedBuilder.build_move(
                member,
                before_channel.name,
                after_channel.name,
                timestamp,
            )
            await self._persist_and_send(
                guild_id=member.guild.id,
                event_type="voice_move",
                actor_id=member.id,
                actor_name=str(member),
                target_id=member.id,
                target_name=str(member),
                details={"before_channel": before_channel.name, "after_channel": after_channel.name},
                embed=embed,
            )
            logger.debug("Logged voice move for user %s from %s to %s", member.id, before_channel.name, after_channel.name)

        elif before_channel:
            embed = VoiceLogEmbedBuilder.build_leave(
                member,
                before_channel.name,
                timestamp,
            )

            await self._persist_and_send(
                guild_id=member.guild.id,
                event_type="voice_leave",
                actor_id=member.id,
                actor_name=str(member),
                target_id=member.id,
                target_name=str(member),
                details={"channel": before_channel.name},
                embed=embed,
            )

            logger.debug("Logged voice leave for user %s from %s", member.id, before_channel.name)

        elif after_channel:
            embed = VoiceLogEmbedBuilder.build_join(
                member,
                after_channel.name,
                timestamp,
            )

            await self._persist_and_send(
                guild_id=member.guild.id,
                event_type="voice_join",
                actor_id=member.id,
                actor_name=str(member),
                target_id=member.id,
                target_name=str(member),
                details={"channel": after_channel.name},
                embed=embed,
            )

            logger.debug("Logged voice join for user %s to %s", member.id, after_channel.name)

    async def log_channel_create(
        self,
        channel: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        moderator: disnake.Member = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        embed = ChannelCreateEmbedBuilder.build_create(channel, moderator, timestamp or datetime.now(timezone.utc))
        
        await self._persist_and_send(
            guild_id=channel.guild.id,
            event_type="channel_create",
            source_channel_id=channel.id,
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=channel.id,
            target_name=channel.name,
            details=self._channel_details(channel),
            embed=embed,
        )

        logger.info("Logged channel create for channel %s", channel.id)
    
    async def log_channel_delete(
        self,
        channel: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        moderator: disnake.Member = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        embed = ChannelDeleteEmbedBuilder.build_delete(channel, moderator, timestamp or datetime.now(timezone.utc))
        await self._persist_and_send(
            guild_id=channel.guild.id,
            event_type="channel_delete",
            source_channel_id=channel.id,
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=channel.id,
            target_name=channel.name,
            details=self._channel_details(channel),
            embed=embed,
        )
        logger.info("Logged channel delete for channel %s", channel.id)

    async def log_channel_update(
        self,
        before: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        after: Union[disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel, disnake.ForumChannel],
        moderator: disnake.Member = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        changes = self._detect_channel_changes(before, after)
        if not changes:
            logger.debug("Skipping channel update for channel %s without visible changes", after.id)
            return

        embed = ChannelLogEmbedBuilder.build_update(after, changes, moderator, timestamp or datetime.now(timezone.utc))
        
        await self._persist_and_send(
            guild_id=after.guild.id,
            event_type="channel_update",
            source_channel_id=after.id, 
            actor_id=moderator.id if moderator else None,
            actor_name=str(moderator) if moderator else None,
            target_id=after.id,
            target_name=after.name,
            details={**self._channel_details(after), "changes": changes},
            embed=embed,
        )

        logger.info("Logged channel update for channel %s, changes: %s", after.id, changes)

    async def log_voice_owner_transfer(
        self,
        channel: disnake.VoiceChannel,
        old_owner: disnake.Member,
        new_owner: disnake.Member,
        timestamp: Optional[datetime] = None,
    ) -> None:
        embed = VoiceOwnerTransferEmbedBuilder.build_transfer(
            channel,
            old_owner,
            new_owner,
            timestamp or datetime.now(timezone.utc),
        )
        await self._persist_and_send(
            guild_id=channel.guild.id,
            event_type="voice_owner_transfer",
            source_channel_id=channel.id,
            actor_id=old_owner.id,
            actor_name=str(old_owner),
            target_id=new_owner.id,
            target_name=str(new_owner),
            details={"channel_id": channel.id, "old_owner_id": old_owner.id, "new_owner_id": new_owner.id},
            embed=embed,
        )
        logger.info("Logged voice owner transfer channel_id=%s old_owner_id=%s new_owner_id=%s", channel.id, old_owner.id, new_owner.id)

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

        logger.info("Logged moderation action %s on user %s by %s", action_type.value, target.id, moderator.id)

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

        logger.info("Logged audit mute for user %s, duration %s", target.id, duration_seconds)

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

        logger.info("Logged audit unmute for user %s", target.id)

    async def log_audit_ban(
        self,
        moderator: disnake.Member,
        target: Union[disnake.Member, disnake.User],
        reason: str,
        *,
        guild_id: Optional[int] = None,
    ) -> None:
        resolved_guild_id = target.guild.id if isinstance(target, disnake.Member) else guild_id
        
        if not resolved_guild_id:
            logger.warning("Unable to determine guild_id for ban audit log, target=%s, moderator=%s", target.id, moderator.id)
            return
        
        embed = ModerationBanEmbedBuilder.build_ban(
            moderator=moderator,
            target=target,
            reason=reason,
            duration_seconds=None,
        )

        await self._persist_and_send(
            guild_id=resolved_guild_id,
            event_type="moderation_audit_ban",
            actor_id=moderator.id,
            actor_name=str(moderator),
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason},
            embed=embed,
        )

        logger.info("Logged audit ban for user %s by %s", target.id, moderator.id)
    
    async def log_audit_unban(
        self,
        moderator: disnake.Member,
        target: Union[disnake.Member, disnake.User],
        reason: str,
        *,
        guild_id: Optional[int] = None,
    ) -> None:
        resolved_guild_id = target.guild.id if isinstance(target, disnake.Member) else guild_id
        
        if not resolved_guild_id:
            logger.warning("Unable to determine guild_id for unban audit log, target=%s, moderator=%s", target.id, moderator.id)
            return
        
        embed = ModerationBanEmbedBuilder.build_unban(
            moderator=moderator,
            target=target,
            reason=reason,
        )

        await self._persist_and_send(
            guild_id=resolved_guild_id,
            event_type="moderation_audit_unban",
            actor_id=moderator.id,
            actor_name=str(moderator),
            target_id=target.id,
            target_name=str(target),
            details={"reason": reason},
            embed=embed,
        )
        
        logger.info("Logged audit unban for user %s by %s", target.id, moderator.id)

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
        
        logger.info("Logged audit kick for user %s", target.id)

    async def cleanup_expired(self) -> None:
        cutoff = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._message_repo.cleanup_expired(cutoff)
        await self._guild_event_repo.cleanup_expired(cutoff)
        if self._database_manager is not None:
            deleted = await self._database_manager.cleanup_retention(
                message_retention_days=self._config.message_log_retention_days,
                punishment_retention_days=self._config.punishment_retention_days,
            )
            logger.info(
                "Retention cleanup completed messages=%s punishments=%s",
                deleted["messages"],
                deleted["punishments"],
            )

    @property
    def retention_cleanup_interval_hours(self) -> int:
        return max(1, self._config.retention_cleanup_interval_hours)

    async def _persist_and_send(
        self,
        *,
        guild_id: Optional[int],
        event_type: str,
        source_channel_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        embed: Optional[disnake.Embed] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        if embed is None:
            embed = self._build_embed(event_type, details)

        await self._guild_event_repo.add(
            GuildEventLogDTO(
                guild_id=guild_id,
                channel_id=source_channel_id,
                actor_id=actor_id,
                actor_name=actor_name,
                target_id=target_id,
                target_name=target_name,
                event_type=event_type,
                details=self._serialize_details(details, embed),
                created_at=now,
                retention_until=self._retention_until(),
            )
        )

        if guild_id is not None:
            try:
                await self._audit_log_service.send_to_log_channel(
                    guild_id, embed, channel_id=None, event_type=event_type
                )
            except TypeError as exc:
                if "event_type" not in str(exc):
                    raise
                await self._audit_log_service.send_to_log_channel(
                    guild_id, embed, channel_id=None
                )

        logger.debug("Persisted and sent event %s for guild %s", event_type, guild_id)

    def _serialize_details(
        self,
        details: Optional[Dict[str, Any]],
        embed: disnake.Embed,
    ) -> Optional[str]:
        payload: Dict[str, Any] = {
            key: value for key, value in (details or {}).items() if value is not None
        }
        embed_data = embed.to_dict()
        for key in ("title", "description"):
            if embed_data.get(key) and key not in payload:
                payload[key] = embed_data[key]
        for key in ("fields", "author", "footer"):
            if embed_data.get(key) and key not in payload:
                payload[key] = embed_data[key]

        if not payload:
            return None
        logger.debug("Serializing event details keys=%s", sorted(payload))
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _channel_details(channel: Any) -> Dict[str, Any]:
        category = getattr(channel, "category", None)
        return {
            "channel": {"id": channel.id, "name": channel.name},
            "channel_type": str(getattr(channel, "type", type(channel).__name__)),
            "category": getattr(category, "name", None),
            "position": getattr(channel, "position", None),
        }

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
        details: Optional[Dict[str, Any]],
    ) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"Событие: {event_type}",
            description=self._format_details(details),
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc),
        )

        return embed

    def _build_member_event_embed(
        self,
        event_type: EventType,
        member: disnake.Member,
        details: Optional[Dict[str, Any]],
    ) -> disnake.Embed:
        timestamp = datetime.now(timezone.utc)
        if event_type == EventType.MEMBER_LEAVE:
            return MemberEventEmbedBuilder.build_leave(member, timestamp)
        if event_type == EventType.MEMBER_UPDATE:
            changes = details.get("changes", []) if details else []
            pending_change = self._parse_pending_change(changes)
            if pending_change:
                return MemberEventEmbedBuilder.build_pending_update(member, pending_change[0], pending_change[1], timestamp)
            return MemberEventEmbedBuilder.build_update(member, [str(change) for change in changes], timestamp)
        return self._build_embed(event_type.value, details)

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
    
    def _detect_channel_changes(self, before, after) -> List[str]:
        """Сравнивает атрибуты каналов и возвращает список изменений."""

        changes = []
        if before.name != after.name:
            changes.append(f"Название: `{before.name}` → `{after.name}`")
            
        if before.position != after.position:
            changes.append(f"Позиция: {before.position} → {after.position}")

        if hasattr(before, "topic") and hasattr(after, "topic") and before.topic != after.topic:
            changes.append(f"Тема: `{before.topic}` → `{after.topic}`")

        if hasattr(before, "slowmode_delay") and hasattr(after, "slowmode_delay") and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"Slowmode: {before.slowmode_delay}с → {after.slowmode_delay}с")

        if hasattr(before, "rate_limit_per_user") and hasattr(after, "rate_limit_per_user") and before.rate_limit_per_user != after.rate_limit_per_user:
            changes.append(f"Slowmode: {before.rate_limit_per_user}с → {after.rate_limit_per_user}с")

        if hasattr(before, "nsfw") and hasattr(after, "nsfw") and before.nsfw != after.nsfw:
            changes.append(f"NSFW: {'вкл' if after.nsfw else 'выкл'}")

        if hasattr(before, "bitrate") and hasattr(after, "bitrate") and before.bitrate != after.bitrate:
            changes.append(f"Битрейт: {before.bitrate} → {after.bitrate}")

        if hasattr(before, "user_limit") and hasattr(after, "user_limit") and before.user_limit != after.user_limit:
            changes.append(f"Лимит пользователей: {before.user_limit} → {after.user_limit}")

        if hasattr(before, "rtc_region") and hasattr(after, "rtc_region") and before.rtc_region != after.rtc_region:
            changes.append(f"Регион: {before.rtc_region} → {after.rtc_region}")

        if hasattr(before, "video_quality_mode") and hasattr(after, "video_quality_mode") and before.video_quality_mode != after.video_quality_mode:
            changes.append(f"Качество видео: {before.video_quality_mode} → {after.video_quality_mode}")

        if hasattr(before, "status") and hasattr(after, "status") and before.status != after.status:
            before_status = before.status or "нет"
            after_status = after.status or "нет"
            changes.append(f"Статус голосового канала: `{before_status}` → `{after_status}`")

        if hasattr(before, "overwrites") and hasattr(after, "overwrites"):
            if before.overwrites != after.overwrites:
                voice_admin_change = self._detect_voice_admin_overwrite_change(before, after)
                if not voice_admin_change:
                    changes.append("Изменены права доступа (overwrites)")

        if hasattr(before, "category") and hasattr(after, "category") and before.category != after.category:
            before_cat = before.category.name if before.category else "нет"
            after_cat = after.category.name if after.category else "нет"
            changes.append(f"Категория: {before_cat} → {after_cat}")

        if hasattr(before, "default_auto_archive_duration") and hasattr(after, "default_auto_archive_duration"):
            if before.default_auto_archive_duration != after.default_auto_archive_duration:
                changes.append(f"Время архивации: {before.default_auto_archive_duration} → {after.default_auto_archive_duration}")

        if hasattr(before, "default_thread_rate_limit_per_user") and hasattr(after, "default_thread_rate_limit_per_user"):
            if before.default_thread_rate_limit_per_user != after.default_thread_rate_limit_per_user:
                changes.append(f"Лимит сообщений в треде: {before.default_thread_rate_limit_per_user} → {after.default_thread_rate_limit_per_user}")

        if hasattr(before, "default_forum_layout") and hasattr(after, "default_forum_layout"):
            if before.default_forum_layout != after.default_forum_layout:
                changes.append(f"Раскладка форума: {before.default_forum_layout} → {after.default_forum_layout}")
        
        if hasattr(before, "default_sort_order") and hasattr(after, "default_sort_order"):
            if before.default_sort_order != after.default_sort_order:
                changes.append(f"Сортировка: {before.default_sort_order} → {after.default_sort_order}")
        
        if hasattr(before, "available_tags") and hasattr(after, "available_tags"):
            if len(before.available_tags) != len(after.available_tags) or \
               any(bt.name != at.name or bt.emoji != at.emoji for bt, at in zip(before.available_tags, after.available_tags)):
                changes.append("Изменены теги форума")
        
        if hasattr(before, "default_reaction_emoji") and hasattr(after, "default_reaction_emoji"):
            if before.default_reaction_emoji != after.default_reaction_emoji:
                changes.append(f"Реакция по умолчанию: {before.default_reaction_emoji} → {after.default_reaction_emoji}")
        
        if hasattr(before, "default_thread_rate_limit_per_user") and hasattr(after, "default_thread_rate_limit_per_user"):
            if before.default_thread_rate_limit_per_user != after.default_thread_rate_limit_per_user:
                changes.append(f"Лимит сообщений в тредах: {before.default_thread_rate_limit_per_user} → {after.default_thread_rate_limit_per_user}")
        
        if hasattr(before, "default_auto_archive_duration") and hasattr(after, "default_auto_archive_duration"):
            if before.default_auto_archive_duration != after.default_auto_archive_duration:
                changes.append(f"Время архивации: {before.default_auto_archive_duration} → {after.default_auto_archive_duration}")
        
        if hasattr(before, "flags") and hasattr(after, "flags"):
            if before.flags != after.flags:
                changes.append("Изменены флаги канала (например, инвайты)")

        return changes

    def _detect_voice_admin_overwrite_change(self, before, after) -> Optional[str]:
        if not isinstance(after, disnake.VoiceChannel):
            return None

        before_admins = self._voice_admin_overwrite_ids(before)
        after_admins = self._voice_admin_overwrite_ids(after)
        if before_admins == after_admins:
            return None

        old_value = self._format_member_id_set(before_admins - after_admins)
        new_value = self._format_member_id_set(after_admins - before_admins)
        logger.info(
            "Detected voice admin permission change channel_id=%s removed=%s added=%s",
            after.id,
            old_value,
            new_value,
        )
        return f"Админ динамического войса: {old_value} → {new_value}"

    @staticmethod
    def _parse_pending_change(changes: List[Any]) -> Optional[tuple[bool, bool]]:
        for change in changes:
            text = str(change).strip()
            if not text.startswith("pending:"):
                continue
            _, _, values = text.partition(":")
            before_text, separator, after_text = values.strip().partition("->")
            if not separator:
                return None
            return before_text.strip() == "True", after_text.strip() == "True"
        return None

    def _voice_admin_overwrite_ids(self, channel) -> set[int]:
        admin_ids: set[int] = set()
        for target, overwrite in getattr(channel, "overwrites", {}).items():
            if isinstance(target, disnake.Role):
                continue
            if self._overwrite_grants_voice_admin(overwrite):
                admin_ids.add(int(target.id))
        return admin_ids

    @staticmethod
    def _overwrite_grants_voice_admin(overwrite) -> bool:
        return any(
            getattr(overwrite, permission, None) is True
            for permission in ("manage_channels", "manage_permissions", "move_members")
        )

    @staticmethod
    def _format_member_id_set(values: set[int]) -> str:
        if not values:
            return "нет"
        return ", ".join(f"<@{value}>" for value in sorted(values))
    
    def _detect_role_changes(self, before: disnake.Role, after: disnake.Role) -> List[str]:
        changes = []
        if before.name != after.name:
            changes.append(f"Название: `{before.name}` → `{after.name}`")
        if before.color != after.color:
            changes.append(f"Цвет: `#{before.color.value:06x}` → `#{after.color.value:06x}`")
        if before.position != after.position:
            changes.append(f"Позиция: {before.position} → {after.position}")
        if before.hoist != after.hoist:
            changes.append(f"Отображать отдельно: {'Да' if after.hoist else 'Нет'}")
        if before.mentionable != after.mentionable:
            changes.append(f"Упоминаема: {'Да' if after.mentionable else 'Нет'}")
        if before.permissions != after.permissions:
            changes.append("Изменены права (permissions)")
        if before.icon != after.icon:
            changes.append("Изменена иконка роли")
        return changes

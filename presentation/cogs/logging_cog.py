import disnake
from disnake.ext import commands, tasks
from typing import Optional

from application.services import AuditLogService, LoggingService
from core.domain.value_objects import EventType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class LoggingCog(commands.Cog):
    def __init__(self, logging_service: LoggingService, audit_log_service: AuditLogService):
        self._logging_service = logging_service
        self._audit_log_service = audit_log_service
        self._bot: Optional[commands.Bot] = None

    def cog_load(self):
        self.cleanup_retention.start()
        logger.info("LoggingCog initialized")

    def cog_unload(self):
        self.cleanup_retention.cancel()

    @tasks.loop(hours=6)
    async def cleanup_retention(self):
        try:
            await self._logging_service.cleanup_expired()
        except Exception as exc:
            logger.error("Retention cleanup failed: %s", exc)

    @cleanup_retention.before_loop
    async def before_cleanup(self):
        if self._bot:
            await self._bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if not getattr(after, "guild", None) or not getattr(before, "guild", None) or before.author.bot:
            return
        await self._logging_service.log_message_edit(before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        if not getattr(message, "guild", None) or message.author.bot:
            return
        await self._logging_service.log_message_delete(message)

    @commands.Cog.listener()
    async def on_raw_bulk_delete(self, payload: disnake.RawBulkMessageDeleteEvent):
        guild = self._guild_from_id(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not isinstance(channel, disnake.TextChannel):
            return
        deleted_by = None
        async for entry in guild.audit_logs(limit=5, action=disnake.AuditLogAction.message_delete):
            if entry.target and entry.target.id == payload.channel_id:
                deleted_by = guild.get_member(entry.user.id)
                break
        await self._logging_service.log_bulk_delete([], channel, deleted_by=deleted_by)

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        await self._logging_service.log_member_event(EventType.MEMBER_LEAVE, member)

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        changed = []
        if before.nick != after.nick:
            changed.append(f"nick: {before.nick} -> {after.nick}")
        if before.pending != after.pending:
            changed.append(f"pending: {before.pending} -> {after.pending}")
        if changed:
            await self._logging_service.log_member_event(
                EventType.MEMBER_UPDATE,
                after,
                extra_data={"changes": changed},
            )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
        await self._logging_service.log_channel_event(EventType.CHANNEL_CREATE, channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        await self._logging_service.log_channel_event(EventType.CHANNEL_DELETE, channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        await self._logging_service.log_channel_event(
            EventType.CHANNEL_UPDATE,
            after,
            extra_data={"before_name": before.name, "after_name": after.name},
        )

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        await self._logging_service.log_role_event(EventType.ROLE_CREATE, role)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        await self._logging_service.log_role_event(EventType.ROLE_DELETE, role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        await self._logging_service.log_role_event(
            EventType.ROLE_UPDATE,
            after,
            extra_data={"before_name": before.name, "after_name": after.name},
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ):
        await self._logging_service.log_voice_event(member, before, after)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: disnake.AuditLogEntry):
        if not self._bot:
            return

        action_type = entry.action

        if action_type == disnake.AuditLogAction.ban:
            target = entry.target
            moderator = entry.user
            if isinstance(target, (disnake.Member, disnake.User)):
                await self._logging_service.log_audit_ban(moderator=moderator, target=target, reason=entry.reason)

        elif action_type == disnake.AuditLogAction.kick:
            target = entry.target
            if isinstance(target, disnake.Member):
                await self._logging_service.log_audit_kick(target, entry.reason)

    def _guild_from_id(self, guild_id: int) -> Optional[disnake.Guild]:
        if self._bot:
            return self._bot.get_guild(guild_id)
        return None
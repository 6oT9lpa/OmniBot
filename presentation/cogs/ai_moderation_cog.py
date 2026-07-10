from __future__ import annotations

from datetime import timedelta

import disnake
from disnake.ext import commands

from application.dto.ai_moderation_decision import AiModerationDecision
from application.dto.ai_moderation_request import AiModerationRequest
from application.services.ai_moderation_queue import AiModerationQueue
from application.services.ai_moderation_settings_service import AiModerationSettingsService
from application.services.channel_service import ChannelService
from core.domain.channel_purpose import ChannelPurpose
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class AiModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot, settings_service: AiModerationSettingsService, channel_service: ChannelService, queue: AiModerationQueue) -> None:
        self._bot = bot
        self._settings_service = settings_service
        self._channel_service = channel_service
        self._queue = queue

    async def cog_load(self) -> None:
        await self._queue.start()
        logger.info("AI moderation cog loaded")

    async def shutdown(self) -> None:
        await self._queue.stop()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message) -> None:
        if message.author.bot or message.guild is None or not isinstance(message.channel, disnake.TextChannel):
            return
        if not await self._settings_service.is_enabled_for_channel(message.guild.id, message.channel.id):
            return
        request = AiModerationRequest(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            user_id=message.author.id,
            message_id=message.id,
            raw_text=message.content,
            created_at=message.created_at,
            reply_to_message_id=message.reference.message_id if message.reference else None,
            mention_count=len(message.mentions),
            role_mention_count=len(message.role_mentions),
            channel_mention_count=len(message.channel_mentions),
            has_attachments=bool(message.attachments),
            attachment_count=len(message.attachments),
        )
        if not self._queue.submit(request):
            logger.warning("AI moderation queue rejected message guild_id=%s message_id=%s", message.guild.id, message.id)

    @commands.slash_command(name="set", description="AI moderation settings")
    @commands.has_permissions(administrator=True)
    async def set_group(self, _: disnake.ApplicationCommandInteraction) -> None:
        return None

    @set_group.sub_command(name="ai-channel", description="Enable AI moderation for a text channel")
    async def set_ai_channel(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel) -> None:
        await self._settings_service.add_channel(ctx.guild_id, channel.id)
        await ctx.response.send_message(f"AI moderation enabled for {channel.mention}.", ephemeral=True)

    @commands.slash_command(name="list", description="AI moderation lists")
    @commands.has_permissions(administrator=True)
    async def list_group(self, _: disnake.ApplicationCommandInteraction) -> None:
        return None

    @list_group.sub_command(name="ai-channel", description="List AI-moderated channels")
    async def list_ai_channel(self, ctx: disnake.ApplicationCommandInteraction) -> None:
        channel_ids = await self._settings_service.list_channels(ctx.guild_id)
        channels = [f"<#{channel_id}>" for channel_id in channel_ids]
        await ctx.response.send_message("\n".join(channels) if channels else "No AI-moderated channels configured.", ephemeral=True)

    @commands.slash_command(name="ai-policy", description="Configure guild AI moderation preferences")
    @commands.has_permissions(administrator=True)
    async def ai_policy(self, _: disnake.ApplicationCommandInteraction) -> None:
        return None

    @ai_policy.sub_command(name="label", description="Set risk and action limits for a moderation label")
    async def set_label_policy(self, ctx: disnake.ApplicationCommandInteraction, label: str, min_action: str = "LOG", max_action: str = "BAN", risk_threshold: float = 0) -> None:
        policy = await self._settings_service.get_policy(ctx.guild_id)
        labels = dict(policy.get("labels", {}))
        labels[label.upper()] = {"min_action": min_action.upper(), "max_action": max_action.upper(), "risk_threshold": max(0.0, min(100.0, risk_threshold))}
        policy["labels"] = labels
        await self._settings_service.save_policy(ctx.guild_id, policy)
        await ctx.response.send_message(f"Policy saved for {label.upper()}.", ephemeral=True)

    @ai_policy.sub_command(name="blacklist", description="Set comma-separated blacklist words")
    async def set_blacklist(self, ctx: disnake.ApplicationCommandInteraction, words: str) -> None:
        policy = await self._settings_service.get_policy(ctx.guild_id)
        policy["blacklist_words"] = tuple(item.strip().lower() for item in words.split(",") if item.strip())[:200]
        await self._settings_service.save_policy(ctx.guild_id, policy)
        await ctx.response.send_message("Blacklist preferences saved.", ephemeral=True)

    @ai_policy.sub_command(name="domains", description="Set comma-separated allowed domains")
    async def set_domains(self, ctx: disnake.ApplicationCommandInteraction, domains: str) -> None:
        policy = await self._settings_service.get_policy(ctx.guild_id)
        policy["allowed_domains"] = tuple(item.strip().lower() for item in domains.split(",") if item.strip())[:200]
        await self._settings_service.save_policy(ctx.guild_id, policy)
        await ctx.response.send_message("Domain preferences saved.", ephemeral=True)

    async def handle_decision(self, request: AiModerationRequest, decision: AiModerationDecision) -> None:
        guild = self._bot.get_guild(request.guild_id)
        if guild is None:
            return
        member = guild.get_member(request.user_id)
        channel = guild.get_channel(request.channel_id)
        message = channel.get_partial_message(request.message_id) if isinstance(channel, disnake.TextChannel) else None
        status = "SUCCESS"
        try:
            for action in decision.execution_plan:
                await self._execute_action(guild, member, message, action, decision.dry_run)
                await self._queue.report_action(decision.event_id, action, "DRY_RUN" if decision.dry_run else "SUCCESS", decision.dry_run)
        except Exception:
            status = "FAILED"
            logger.exception("AI moderation action failed guild_id=%s message_id=%s", request.guild_id, request.message_id)
        await self._settings_service.record_event(request.guild_id, request.channel_id, request.message_id, request.user_id, decision.risk_score, decision.action, decision.primary_label, decision.labels, status)
        await self._send_log(guild, decision, status)

    async def _execute_action(self, guild: disnake.Guild, member: disnake.Member | None, message: disnake.PartialMessage | None, action: str, dry_run: bool) -> None:
        if dry_run or action in {"IGNORE", "LOG", "REVIEW"}:
            return
        if action == "DELETE" and message is not None:
            await message.delete(reason="AI moderation policy")
        elif action == "WARN" and member is not None:
            await member.send("Your message was flagged by this server's moderation policy.")
        elif action == "TIMEOUT" and member is not None:
            await member.timeout(duration=timedelta(minutes=10), reason="AI moderation policy")
        elif action == "BAN" and member is not None:
            await guild.ban(member, reason="AI moderation policy")

    async def _send_log(self, guild: disnake.Guild, decision: AiModerationDecision, status: str) -> None:
        channel_id = await self._channel_service.get_purpose_channel(guild.id, ChannelPurpose.AI_MODERATION_LOG)
        channel = guild.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, disnake.TextChannel):
            return
        embed = disnake.Embed(title="AI moderation decision", color=disnake.Color.orange())
        embed.add_field(name="User", value=f"<@{decision.user_id}>", inline=True)
        embed.add_field(name="Risk", value=f"{decision.risk_score:.2f}", inline=True)
        embed.add_field(name="Action", value=decision.action, inline=True)
        embed.add_field(name="Labels", value=", ".join(decision.labels) or decision.primary_label, inline=False)
        embed.set_footer(text=f"message={decision.message_id} event={decision.event_id} status={status}")
        await channel.send(embed=embed)

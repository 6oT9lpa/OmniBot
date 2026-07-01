from __future__ import annotations

import disnake
from disnake.ext import commands, tasks

from application.dto.creator_alert_dto import CreatorAlertSubscriptionInput
from application.services.creator_alert_service import CreatorAlertService
from core.domain.creator_alert import (
    CreatorAlertKind,
    CreatorContentEvent,
    CreatorPlatform,
)
from infrastructure.logging import get_logger
from presentation.embeds.creator_alert_embed import CreatorAlertEmbedBuilder

logger = get_logger(__name__)


class StreamsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, creator_alert_service: CreatorAlertService):
        self._bot = bot
        self._creator_alert_service = creator_alert_service
        logger.info("StreamsCog initialized")

    def cog_load(self) -> None:
        self.monitor_creator_sources.start()
        logger.info("Creator alert monitor started")

    def cog_unload(self) -> None:
        self.monitor_creator_sources.cancel()
        logger.info("Creator alert monitor stopped")

    @tasks.loop(minutes=3)
    async def monitor_creator_sources(self) -> None:
        logger.info("Running creator alert monitor")
        for guild in self._bot.guilds:
            subscriptions = await self._creator_alert_service.list_sources(guild.id)
            for subscription in subscriptions:
                try:
                    event = await self._creator_alert_service.check_subscription(subscription)
                    if not event or subscription.id is None:
                        continue
                    await self._publish_subscription_event(guild, subscription, event)
                    await self._creator_alert_service.mark_announced(subscription.id, event.event_id)
                except Exception as exc:
                    logger.error(
                        "Creator alert monitor failed guild_id=%s subscription_id=%s error=%s",
                        guild.id,
                        subscription.id,
                        exc,
                        exc_info=True,
                    )

    @monitor_creator_sources.before_loop
    async def before_monitor_creator_sources(self) -> None:
        await self._bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_presence_update(self, before: disnake.Member, after: disnake.Member) -> None:
        if before.bot or not after.guild:
            return
        before_stream = self._get_stream_activity(before)
        after_stream = self._get_stream_activity(after)
        if before_stream or not after_stream:
            return

        subscriptions = await self._creator_alert_service.list_sources(after.guild.id, after.id)
        active_stream_sources = [
            source
            for source in subscriptions
            if source.active and source.alert_kind == CreatorAlertKind.STREAM
        ]
        if active_stream_sources:
            logger.info(
                "Skipping Discord activity fallback because active source exists guild_id=%s user_id=%s sources=%s",
                after.guild.id,
                after.id,
                [source.id for source in active_stream_sources],
            )
            return

        event = CreatorContentEvent(
            platform=CreatorPlatform.TWITCH,
            alert_kind=CreatorAlertKind.STREAM,
            event_id=f"discord-activity:{after.id}:{after_stream.name}",
            creator_name=after.display_name,
            title=after_stream.name or "Live stream",
            url=getattr(after_stream, "url", None) or "",
            game=getattr(after_stream, "details", None) or "Just Chatting",
        )
        await self._publish_default_event(after.guild, after.id, event)

    @commands.slash_command(name="streamer", description="Manage creator alert subscriptions")
    async def streamer(self, ctx: disnake.ApplicationCommandInteraction) -> None:
        logger.info("Streamer command group invoked user_id=%s", ctx.author.id)

    @streamer.sub_command(name="add", description="Add a creator source")
    async def streamer_add(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        platform: str = commands.Param(choices=["twitch", "youtube", "kick"]),
        channel_url: str = commands.Param(max_length=2048),
        channel_name: str = commands.Param(default="", max_length=120),
    ) -> None:
        await ctx.response.defer(ephemeral=True)
        try:
            source = await self._creator_alert_service.save_source(
                CreatorAlertSubscriptionInput(
                    guild_id=ctx.guild.id,
                    user_id=ctx.author.id,
                    platform=CreatorPlatform(platform),
                    channel_url=channel_url,
                    channel_name=channel_name or None,
                )
            )
        except ValueError as exc:
            await ctx.edit_original_response(content=str(exc))
            return

        embed = disnake.Embed(
            title="Creator source saved",
            description=f"{source.platform.value.title()} source connected for {source.channel_name or source.channel_url}.",
            color=disnake.Color.green(),
        )
        await ctx.edit_original_response(embed=embed)

    @streamer.sub_command(name="remove", description="Remove a creator source")
    async def streamer_remove(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        source_id: int,
    ) -> None:
        await ctx.response.defer(ephemeral=True)
        removed = await self._creator_alert_service.remove_source(ctx.guild.id, ctx.author.id, source_id)
        message = "Creator source removed" if removed else "Creator source was not found"
        await ctx.edit_original_response(content=message)

    @streamer.sub_command(name="list", description="List creator sources")
    async def streamer_list(self, ctx: disnake.ApplicationCommandInteraction) -> None:
        await ctx.response.defer(ephemeral=True)
        is_admin = bool(ctx.author.guild_permissions.administrator)
        sources = await self._creator_alert_service.list_sources(
            ctx.guild.id,
            None if is_admin else ctx.author.id,
        )
        embed = disnake.Embed(title="Creator sources", color=0x5865F2)
        if not sources:
            embed.description = "No creator sources connected yet."
        for source in sources[:10]:
            embed.add_field(
                name=f"#{source.id} {source.platform.value.title()} / {source.alert_kind.value}",
                value=f"{source.channel_name or source.channel_url}\nActive: {source.active}",
                inline=False,
            )
        await ctx.edit_original_response(embed=embed)

    @commands.slash_command(name="stream-template", description="Manage creator alert embed templates")
    async def stream_template(self, ctx: disnake.ApplicationCommandInteraction) -> None:
        logger.info("Stream template command group invoked user_id=%s", ctx.author.id)

    @stream_template.sub_command(name="set", description="Set the default template for a creator source")
    async def stream_template_set(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        source_id: int,
        title_template: str = commands.Param(default="{creator.name} is live on {platform}", max_length=256),
        description_template: str = commands.Param(
            default="{creator.ping} {creator.name} started streaming {game}\n{url}",
            max_length=2000,
        ),
        ping_role: disnake.Role | None = None,
    ) -> None:
        await ctx.response.defer(ephemeral=True)
        source = await self._creator_alert_service.get_source_for_user(ctx.guild.id, ctx.author.id, source_id)
        if not source:
            await ctx.edit_original_response(content="Creator source was not found")
            return
        saved = await self._creator_alert_service.save_source(
            CreatorAlertSubscriptionInput(
                guild_id=source.guild_id,
                user_id=source.user_id,
                platform=source.platform,
                channel_url=source.channel_url,
                channel_name=source.channel_name,
                external_channel_id=source.external_channel_id,
                alert_kind=source.alert_kind,
                title_template=title_template,
                description_template=description_template,
                button_label=source.button_label,
                color=source.color,
                ping_role_id=ping_role.id if ping_role else source.ping_role_id,
                active=source.active,
            )
        )
        embed = disnake.Embed(
            title="Stream template saved",
            description=f"Template updated for source #{saved.id}.",
            color=disnake.Color.green(),
        )
        await ctx.edit_original_response(embed=embed)

    async def _publish_subscription_event(
        self,
        guild: disnake.Guild,
        subscription,
        event: CreatorContentEvent,
    ) -> None:
        channel_id = await self._creator_alert_service.get_announce_channel_id(guild.id)
        channel = await self._resolve_text_channel(guild, channel_id)
        if not isinstance(channel, disnake.TextChannel):
            logger.warning("Stream announce channel is not configured guild_id=%s", guild.id)
            return

        ping_role_id = subscription.ping_role_id or await self._creator_alert_service.get_default_ping_role_id(guild.id)
        creator_ping = f"<@&{ping_role_id}>" if ping_role_id else f"<@{subscription.user_id}>"
        embed = CreatorAlertEmbedBuilder.build(
            event,
            title_template=subscription.title_template,
            description_template=subscription.description_template,
            color=CreatorAlertEmbedBuilder.platform_color(event.platform, subscription.color),
            creator_ping=creator_ping,
        )
        content = creator_ping if ping_role_id else ""
        await channel.send(content=content, embed=embed, allowed_mentions=disnake.AllowedMentions(roles=True, users=False))
        logger.info(
            "Published creator alert guild_id=%s subscription_id=%s event_id=%s",
            guild.id,
            subscription.id,
            event.event_id,
        )

    async def _publish_default_event(
        self,
        guild: disnake.Guild,
        user_id: int,
        event: CreatorContentEvent,
    ) -> None:
        channel_id = await self._creator_alert_service.get_announce_channel_id(guild.id)
        channel = await self._resolve_text_channel(guild, channel_id)
        if not isinstance(channel, disnake.TextChannel):
            logger.warning("Default stream announce skipped because channel is missing guild_id=%s", guild.id)
            return
        ping_role_id = await self._creator_alert_service.get_default_ping_role_id(guild.id)
        content = f"<@&{ping_role_id}>" if ping_role_id else ""
        embed = CreatorAlertEmbedBuilder.build(
            event,
            title_template="{creator.name} is live on {platform}",
            description_template="{creator.ping} {title}\nGame: {game}\n{url}",
            color=CreatorAlertEmbedBuilder.platform_color(event.platform),
            creator_ping=f"<@{user_id}>",
        )
        await channel.send(content=content, embed=embed, allowed_mentions=disnake.AllowedMentions(roles=True, users=False))
        logger.info("Published Discord activity fallback stream alert guild_id=%s user_id=%s", guild.id, user_id)

    def _get_stream_activity(self, member: disnake.Member) -> disnake.Streaming | None:
        for activity in member.activities:
            if isinstance(activity, disnake.Streaming):
                return activity
        return None

    async def _resolve_text_channel(
        self,
        guild: disnake.Guild,
        channel_id: int | None,
    ) -> disnake.TextChannel | None:
        if not channel_id:
            return None

        channel = guild.get_channel(channel_id)
        if isinstance(channel, disnake.TextChannel):
            return channel

        try:
            fetched = await self._bot.fetch_channel(channel_id)
        except Exception as exc:
            logger.warning(
                "Failed to fetch stream announce channel guild_id=%s channel_id=%s error=%s",
                guild.id,
                channel_id,
                exc,
            )
            return None
        return fetched if isinstance(fetched, disnake.TextChannel) else None

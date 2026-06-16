from __future__ import annotations

import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from core.interfaces.services.stats_service_interface import StatsServiceInterface
from infrastructure.logging import get_logger
from presentation.embeds.stats_embeds import StatsEmbedBuilder

logger = get_logger(__name__)

MSK = timezone(timedelta(hours=3))


class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, stats_service: StatsServiceInterface) -> None:
        self._bot = bot
        self._service = stats_service
        self._voice_sessions: Dict[int, Dict[int, datetime]] = {}

        if self._service is not None:
            self._service.set_bot(bot)

        self._snapshot_task.start()
        logger.info("StatsCog initialized")

    def cog_unload(self) -> None:
        self._snapshot_task.cancel()

    @tasks.loop(hours=1)
    async def _snapshot_task(self) -> None:
        pass

    @_snapshot_task.before_loop
    async def _before_snapshot(self) -> None:
        await self._bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message) -> None:
        await self._service.log_message(message)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ) -> None:
        if member.bot or not member.guild:
            return

        guild_id = member.guild.id
        user_id = member.id

        if before.channel is None and after.channel is not None:
            self._voice_sessions.setdefault(guild_id, {})[user_id] = datetime.now(MSK)

        elif before.channel is not None and after.channel is None:
            joined_at = self._voice_sessions.get(guild_id, {}).pop(user_id, None)
            if joined_at:
                await self._service.log_voice_activity(member, joined_at)

        elif before.channel != after.channel:
            joined_at = self._voice_sessions.get(guild_id, {}).pop(user_id, None)
            if joined_at:
                await self._service.log_voice_activity(member, joined_at)
            self._voice_sessions.setdefault(guild_id, {})[user_id] = datetime.now(MSK)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member) -> None:
        await self._service.log_member_join(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member) -> None:
        await self._service.log_member_leave(member)

    @commands.slash_command(description="📊 Статистика сервера и участников")
    async def stats(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @stats.sub_command(description="Общая статистика сервера за 7 или 30 дней")
    async def server(
        self,
        inter: disnake.ApplicationCommandInteraction,
        period: int = commands.Param(7, choices=[7, 30]),
    ) -> None:
        await inter.response.defer(ephemeral=True)
        data = await self._service.get_server_stats(inter.guild.id, period)
        embed = StatsEmbedBuilder.build_server_stats(data, period, inter.guild)
        await inter.edit_original_response(embed=embed)

    @stats.sub_command(description="Статистика участника (включая наказания)")
    async def user(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User = None,
    ) -> None:
        await inter.response.defer(ephemeral=True)
        user = user or inter.author
        stats = await self._service.get_user_stats(user.id, inter.guild.id)
        if not stats:
            await self._service.log_member_join(inter.guild.get_member(user.id) or user)
            stats = await self._service.get_user_stats(user.id, inter.guild.id)
        if not stats:
            await inter.edit_original_response(
                f"❌ {user.display_name} ещё не отправлял сообщений на сервере."
            )
            return
        embed = StatsEmbedBuilder.build_user_stats(user, stats, inter.guild)
        await inter.edit_original_response(embed=embed)

    @stats.sub_command(description="Топ-5 самых активных каналов за неделю")
    async def channels(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        top = await self._service.get_top_channels(inter.guild.id, days=7, limit=5)
        if not top:
            await inter.edit_original_response("Нет активных каналов.")
            return
        embed = StatsEmbedBuilder.build_top_channels(top, inter.guild)
        await inter.edit_original_response(embed=embed)

    @stats.sub_command(description="График активности по часам (последние 7 дней)")
    async def activity(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        hourly = await self._service.get_activity_by_hour(inter.guild.id, days=7)
        embed = StatsEmbedBuilder.build_activity_graph(hourly)
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(description="🏆 Топ-10 самых активных участников за неделю")
    async def leaderboard(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        top = await self._service.get_leaderboard(inter.guild.id, days=7, limit=10)
        if not top:
            await inter.edit_original_response("📊 Нет данных. Напишите что-нибудь в чат!")
            return
        embed = StatsEmbedBuilder.build_leaderboard(top, inter.guild, self._bot)
        await inter.edit_original_response(embed=embed)

    @stats.sub_command(description="📈 Статистика каналов за последние 24 часа")
    async def channel_stats(
        self,
        inter: disnake.ApplicationCommandInteraction,
    ) -> None:
        await inter.response.defer(ephemeral=True)
        data = await self._service.get_channel_stats_24h(inter.guild.id)
        embed = StatsEmbedBuilder.build_channel_stats_24h(data, inter.guild)
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(description="📊 Активность участников за 7 дней")
    async def status(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    
from __future__ import annotations

import disnake
from disnake.ext import commands
from typing import Optional

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger
from presentation.views.voice_views import VoiceControlView

logger = get_logger(__name__)


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot, service: VoiceServiceInterface) -> None:
        self._bot = bot
        self._service = service
        self._trigger_cache: Optional[int] = None
        self._bot.loop.create_task(self._on_start())

    async def _on_start(self) -> None:
        await self._bot.wait_until_ready()
        for guild in self._bot.guilds:
            trigger = await self._service.get_trigger(guild.id)
            if trigger is not None:
                self._trigger_cache = trigger
                break
        logger.info("VoiceCog loaded, trigger_id=%s", self._trigger_cache)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ) -> None:
        if member.bot:
            return

        guild = member.guild
        trigger_id = await self._service.get_trigger(guild.id) or self._trigger_cache

        # Вход в триггерный канал
        if after.channel and trigger_id and after.channel.id == trigger_id:
            existing = await self._service._repo.get_by_owner(member.id, guild.id)
            if existing:
                ch = guild.get_channel(existing["channel_id"])
                if ch and ch.id != after.channel.id:
                    try:
                        await member.move_to(ch)
                    except Exception as exc:
                        logger.warning("Failed to redirect member %s: %s", member.id, exc)
                    return
            else:
                channel = await self._service.create(member, after.channel)
                if channel:
                    embed = disnake.Embed(
                        title="🎛️ Управление комнатой",
                        color=disnake.Color.green(),
                    )
                    embed.add_field(name="👑 Владелец", value=member.mention, inline=True)
                    embed.set_footer(text="Меню снизу")
                    await channel.send(embed=embed, view=VoiceControlView(self._service))
            return

        # Выход из комнаты
        if before.channel:
            room = await self._service._repo.get(before.channel.id)
            if room:
                if room["owner_id"] == member.id and len(before.channel.members) > 0:
                    await self._service.handle_owner_leave(before.channel, member)
                if len(before.channel.members) == 0:
                    await self._service.schedule_delete(before.channel)

        # Вход в существующую комнату
        if after.channel:
            room = await self._service._repo.get(after.channel.id)
            if room:
                await self._service.cancel_delete(after.channel.id)

    @commands.slash_command(description="🎤 Голосовые комнаты")
    async def voice(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @voice.sub_command(description="Установить триггер (админ)")
    async def set_trigger(
        self,
        inter: disnake.ApplicationCommandInteraction,
        канал: disnake.VoiceChannel,
    ) -> None:
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("❌ Только админ!", ephemeral=True)
            return

        await self._service.set_trigger(inter.guild.id, канал.id)
        self._trigger_cache = канал.id
        await inter.response.send_message(f"✅ {канал.mention} установлен как триггер.", ephemeral=True)

    @voice.sub_command(description="Удалить триггер (админ)")
    async def remove_trigger(self, inter: disnake.ApplicationCommandInteraction) -> None:
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("❌ Только админ!", ephemeral=True)
            return

        await self._service.remove_trigger(inter.guild.id)
        self._trigger_cache = None
        await inter.response.send_message("✅ Триггер удалён.", ephemeral=True)
from __future__ import annotations

from typing import List, Optional

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VoiceControlView(disnake.ui.View):
    def __init__(self, service: VoiceServiceInterface) -> None:
        super().__init__(timeout=None)
        self.service = service

    @disnake.ui.string_select(
        placeholder="🎛️ Выберите действие...",
        custom_id="voice_actions",
        options=[
            disnake.SelectOption(label="✏️ Переименовать", value="rename", emoji="✏️"),
            disnake.SelectOption(label="👥 Лимит", value="limit", emoji="👥"),
            disnake.SelectOption(label="🔒 Закрыть", value="lock", emoji="🔒"),
            disnake.SelectOption(label="🔓 Открыть", value="unlock", emoji="🔓"),
            disnake.SelectOption(label="📩 Пригласить", value="invite", emoji="📩"),
            disnake.SelectOption(label="👢 Выгнать", value="kick", emoji="👢"),
            disnake.SelectOption(label="🔄 Передать", value="transfer", emoji="🔄"),
            disnake.SelectOption(label="🌍 Регион", value="region", emoji="🌍"),
            disnake.SelectOption(label="🗑️ Удалить", value="delete", emoji="🗑️"),
            disnake.SelectOption(label="🔨 Забанить", value="ban", emoji="🔨"),
        ]
    )
    async def voice_actions(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction) -> None:
        vc = inter.author.voice.channel if inter.author.voice else None
        if not vc:
            await inter.response.send_message("❌ Вы не в голосовом канале!", ephemeral=True)
            return

        action = select.values[0]

        try:
            if action == "rename":
                await inter.response.send_modal(VoiceRenameModal(self.service))
            elif action == "limit":
                await inter.response.send_modal(VoiceLimitModal(self.service))
            elif action == "lock":
                await self.service.lock(vc, inter.author)
                await inter.response.send_message("🔒 Закрыто!", ephemeral=True)
            elif action == "unlock":
                await self.service.unlock(vc, inter.author)
                await inter.response.send_message("🔓 Открыто!", ephemeral=True)
            elif action == "invite":
                await inter.response.send_modal(VoiceInviteModal(self.service))
            elif action == "kick":
                members = [m for m in vc.members if not m.bot and m.id != inter.author.id]
                if not members:
                    await inter.response.send_message("❌ Некого!", ephemeral=True)
                    return
                view = MemberSelectView(self.service, vc, "kick", members)
                await inter.response.send_message("👢 Выберите:", view=view, ephemeral=True)
            elif action == "transfer":
                members = [m for m in vc.members if not m.bot and m.id != inter.author.id]
                if not members:
                    await inter.response.send_message("❌ Некому!", ephemeral=True)
                    return
                view = MemberSelectView(self.service, vc, "transfer", members)
                await inter.response.send_message("🔄 Выберите:", view=view, ephemeral=True)
            elif action == "region":
                view = RegionSelectView(vc)
                await inter.response.send_message("🌍 Выберите:", view=view, ephemeral=True)
            elif action == "delete":
                if not vc.permissions_for(inter.author).manage_channels:
                    await inter.response.send_message("❌ Нет прав!", ephemeral=True)
                    return
                await self.service.delete(vc)
                await inter.response.send_message("🗑️ Удалено!", ephemeral=True)
            elif action == "ban":
                members = [m for m in vc.members if not m.bot and m.id != inter.author.id]
                if not members:
                    await inter.response.send_message("❌ Некого!", ephemeral=True)
                    return
                view = MemberSelectView(self.service, vc, "ban", members)
                await inter.response.send_message("🔨 Выберите кого забанить:", view=view, ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            logger.error("Voice action error: %s", exc)
            await inter.response.send_message("❌ Произошла ошибка", ephemeral=True)


class MemberSelectView(disnake.ui.View):
    def __init__(
        self,
        service: VoiceServiceInterface,
        channel: disnake.VoiceChannel,
        action: str,
        members: List[disnake.Member],
    ) -> None:
        super().__init__(timeout=60)
        self.service = service
        self.channel = channel
        self.action = action
        options = [
            disnake.SelectOption(label=m.display_name[:100], value=str(m.id), emoji="👤")
            for m in members[:25]
        ]
        menu = disnake.ui.StringSelect(placeholder="Выберите...", custom_id="member_select", options=options)
        menu.callback = self.callback
        self.add_item(menu)

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        target = inter.guild.get_member(int(inter.data["values"][0]))
        if not target:
            await inter.response.send_message("❌ Не найден!", ephemeral=True)
            return

        try:
            if self.action == "kick":
                await self.service.kick(self.channel, target, inter.author)
                await inter.response.send_message("✅ Выгнан!", ephemeral=True)
            elif self.action == "transfer":
                await self.service.transfer(self.channel, target, inter.author)
                view = VoiceControlView(self.service)
                async for msg in self.channel.history(limit=5):
                    if msg.author == inter.guild.me and msg.embeds:
                        embed = msg.embeds[0]
                        embed.set_field_at(0, name="👑 Владелец", value=target.mention, inline=True)
                        await msg.edit(embed=embed, view=view)
                        break
                await inter.response.send_message("✅ Передано!", ephemeral=True)
            elif self.action == "ban":
                await self.service.ban(self.channel, target, inter.author)
                await inter.response.send_message("🔨 Забанен!", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            logger.error("Member select error: %s", exc)
            await inter.response.send_message("❌ Произошла ошибка", ephemeral=True)
        self.stop()


class RegionSelectView(disnake.ui.View):
    REGIONS = [
        ("🇧🇷 Бразилия", "brazil"),
        ("🇳🇱 Роттердам", "rotterdam"),
        ("🇮🇳 Индия", "india"),
        ("🇯🇵 Япония", "japan"),
        ("🇸🇬 Сингапур", "singapore"),
        ("🇿🇦 ЮАР", "southafrica"),
        ("🇦🇺 Сидней", "sydney"),
        ("🇪🇺 Европа", "europe"),
        ("🇺🇸 US East", "us-east"),
        ("🇺🇸 US West", "us-west"),
        ("🇺🇸 US Central", "us-central"),
        ("🇺🇸 US South", "us-south"),
    ]

    def __init__(self, channel: disnake.VoiceChannel) -> None:
        super().__init__(timeout=60)
        self.channel = channel
        options = [disnake.SelectOption(label=l, value=v) for l, v in self.REGIONS]
        menu = disnake.ui.StringSelect(placeholder="🌍 Регион...", custom_id="region_select", options=options[:25])
        menu.callback = self.callback
        self.add_item(menu)

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        region = inter.data["values"][0]
        if not self.channel.permissions_for(inter.author).manage_channels:
            await inter.response.send_message("❌ Нет прав!", ephemeral=True)
            return

        try:
            await self.channel.edit(rtc_region=region)
            await inter.response.send_message(f"🌍 Регион изменён на {region}", ephemeral=True)
        except Exception as exc:
            logger.error("Failed to change region: %s", exc)
            await inter.response.send_message("❌ Ошибка при изменении региона", ephemeral=True)
        self.stop()


class VoiceRenameModal(disnake.ui.Modal):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            title="✏️ Переименовать",
            components=[
                disnake.ui.TextInput(
                    label="Название",
                    placeholder="Моя комната",
                    custom_id="name",
                    min_length=1,
                    max_length=100,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        vc = inter.author.voice.channel if inter.author.voice else None
        if not vc:
            await inter.response.send_message("❌ Не в канале!", ephemeral=True)
            return

        try:
            await self.service.rename(vc, inter.text_values["name"], inter.author)
            await inter.response.send_message("✅ Готово!", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            logger.error("Rename error: %s", exc)
            await inter.response.send_message("❌ Произошла ошибка", ephemeral=True)


class VoiceLimitModal(disnake.ui.Modal):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            title="👥 Лимит",
            components=[
                disnake.ui.TextInput(
                    label="Лимит (0 — без лимита)",
                    placeholder="0",
                    custom_id="limit",
                    min_length=1,
                    max_length=2,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        vc = inter.author.voice.channel if inter.author.voice else None
        if not vc:
            await inter.response.send_message("❌ Не в канале!", ephemeral=True)
            return

        try:
            limit = int(inter.text_values["limit"])
            await self.service.set_limit(vc, limit, inter.author)
            await inter.response.send_message(f"👥 {limit if limit > 0 else 'без лимита'}", ephemeral=True)
        except ValueError:
            await inter.response.send_message("❌ Введите число!", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            logger.error("Limit error: %s", exc)
            await inter.response.send_message("❌ Произошла ошибка", ephemeral=True)


class VoiceInviteModal(disnake.ui.Modal):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            title="📩 Пригласить",
            components=[
                disnake.ui.TextInput(
                    label="ID пользователя",
                    placeholder="123456789",
                    custom_id="user_id",
                    min_length=1,
                    max_length=20,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        vc = inter.author.voice.channel if inter.author.voice else None
        if not vc:
            await inter.response.send_message("❌ Не в канале!", ephemeral=True)
            return

        raw = inter.text_values["user_id"].strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            target = inter.guild.get_member(int(raw))
            if not target:
                await inter.response.send_message("❌ Пользователь не найден!", ephemeral=True)
                return
        except ValueError:
            await inter.response.send_message("❌ Неверный ID!", ephemeral=True)
            return

        try:
            await self.service.invite(vc, target, inter.author)
            await inter.response.send_message(f"✅ {target.mention} приглашён!", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            logger.error("Invite error: %s", exc)
            await inter.response.send_message("❌ Произошла ошибка", ephemeral=True)
from __future__ import annotations

from typing import Callable, Optional

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger
from presentation.views.voice_control.member_select_view import MemberSelectView
from presentation.views.voice_control.panel_refresh import refresh_voice_control_panel
from presentation.views.voice_control.voice_invite_modal import VoiceInviteModal
from presentation.views.voice_control.voice_limit_modal import VoiceLimitModal
from presentation.views.voice_control.voice_rename_modal import VoiceRenameModal

logger = get_logger(__name__)


class VoiceActionSelectView(disnake.ui.View):
    def __init__(
        self,
        service: VoiceServiceInterface,
        channel: disnake.VoiceChannel,
        room: dict,
        actor: disnake.Member,
    ) -> None:
        super().__init__(timeout=60)
        self.service = service
        self.channel = channel
        self.room = room
        self.actor = actor
        options = self._build_options()
        self.has_actions = bool(options)
        if options:
            select = VoiceActionSelect(service, channel, room, options)
            self.add_item(select)

    def _build_options(self) -> list[disnake.SelectOption]:
        is_owner = int(self.room["owner_id"]) == self.actor.id
        admin_id = int(self.room["admin_id"]) if self.room.get("admin_id") else None
        is_admin = admin_id == self.actor.id
        if not is_owner and not is_admin:
            return []

        options = [
            disnake.SelectOption(label="Rename", value="rename", description="Изменить название"),
            disnake.SelectOption(label="Limit", value="limit", description="Изменить лимит"),
            disnake.SelectOption(label="Lock", value="lock", description="Закрыть комнату"),
            disnake.SelectOption(label="Unlock", value="unlock", description="Открыть комнату"),
            disnake.SelectOption(label="Invite", value="invite", description="Пригласить участника"),
            disnake.SelectOption(label="Kick", value="kick", description="Отключить участника"),
            disnake.SelectOption(label="Ban", value="ban", description="Запретить вход"),
        ]
        if is_owner:
            options.append(disnake.SelectOption(label="Take Admin", value="take_admin", description="Owner забирает управление"))
            if admin_id:
                options.append(disnake.SelectOption(label="Clear Admin", value="clear_admin", description="Owner освобождает admin"))
            else:
                options.append(disnake.SelectOption(label="Assign Admin", value="assign_admin", description="Owner назначает admin"))
        elif is_admin and admin_id:
            options.append(disnake.SelectOption(label="Release Admin", value="release_admin", description="Admin снимает права"))
        return options


class VoiceActionSelect(disnake.ui.StringSelect):
    def __init__(
        self,
        service: VoiceServiceInterface,
        channel: disnake.VoiceChannel,
        room: dict,
        options: list[disnake.SelectOption],
    ) -> None:
        self.service = service
        self.channel = channel
        self.room = room
        super().__init__(
            custom_id=f"voice:actions:{channel.id}",
            placeholder="Действие",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        action = self.values[0]
        logger.info("Voice action selected: action=%s channel_id=%s user_id=%s", action, self.channel.id, inter.author.id)
        handlers: dict[str, Callable[[disnake.MessageInteraction], object]] = {
            "rename": self._rename,
            "limit": self._limit,
            "lock": self._lock,
            "unlock": self._unlock,
            "invite": self._invite,
            "kick": lambda interaction: self._member_action(interaction, "kick"),
            "ban": lambda interaction: self._member_action(interaction, "ban"),
            "take_admin": self._take_admin,
            "assign_admin": lambda interaction: self._member_action(interaction, "assign_admin"),
            "clear_admin": self._clear_admin,
            "release_admin": self._release_admin,
        }
        handler = handlers.get(action)
        if handler is None:
            await inter.response.send_message("Неизвестное действие.", ephemeral=True)
            return
        await handler(inter)

    async def _rename(self, inter: disnake.MessageInteraction) -> None:
        await inter.response.send_modal(VoiceRenameModal(self.service))

    async def _limit(self, inter: disnake.MessageInteraction) -> None:
        await inter.response.send_modal(VoiceLimitModal(self.service))

    async def _lock(self, inter: disnake.MessageInteraction) -> None:
        try:
            await self.service.lock(self.channel, inter.author)
            await inter.response.send_message("Комната закрыта.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    async def _unlock(self, inter: disnake.MessageInteraction) -> None:
        try:
            await self.service.unlock(self.channel, inter.author)
            await inter.response.send_message("Комната открыта.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    async def _invite(self, inter: disnake.MessageInteraction) -> None:
        await inter.response.send_modal(VoiceInviteModal(self.service))

    async def _member_action(self, inter: disnake.MessageInteraction, action: str) -> None:
        members = [member for member in self.channel.members if not member.bot and member.id != inter.author.id]
        if not members:
            await inter.response.send_message("Нет доступных участников.", ephemeral=True)
            return
        await inter.response.send_message(
            "Выберите участника:",
            view=MemberSelectView(self.service, self.channel, action, members),
            ephemeral=True,
        )

    async def _take_admin(self, inter: disnake.MessageInteraction) -> None:
        if not self._is_owner(inter.author):
            await inter.response.send_message("Только Owner может использовать Take Admin.", ephemeral=True)
            return
        await self.service.assign_admin(self.channel, None, inter.author)
        await self._refresh_panel(None)
        await inter.response.send_message("Owner забрал управление.", ephemeral=True)

    async def _clear_admin(self, inter: disnake.MessageInteraction) -> None:
        if not self._is_owner(inter.author):
            await inter.response.send_message("Только Owner может очистить Admin.", ephemeral=True)
            return
        if not self.room.get("admin_id"):
            await inter.response.send_message("Admin уже свободен.", ephemeral=True)
            return
        await self.service.assign_admin(self.channel, None, inter.author)
        await self._refresh_panel(None)
        await inter.response.send_message("Admin освобожден.", ephemeral=True)

    async def _release_admin(self, inter: disnake.MessageInteraction) -> None:
        admin_id = int(self.room["admin_id"]) if self.room.get("admin_id") else None
        if admin_id != inter.author.id:
            await inter.response.send_message("Release Admin доступен только текущему Admin.", ephemeral=True)
            return
        await self.service.release_admin(self.channel, inter.author)
        await self._refresh_panel(None)
        await inter.response.send_message("Admin права сняты.", ephemeral=True)

    async def _refresh_panel(self, admin: Optional[disnake.Member]) -> None:
        owner = self.channel.guild.get_member(int(self.room["owner_id"]))
        if owner:
            await refresh_voice_control_panel(self.service, self.channel, owner, admin)

    def _is_owner(self, member: disnake.Member) -> bool:
        return int(self.room["owner_id"]) == member.id

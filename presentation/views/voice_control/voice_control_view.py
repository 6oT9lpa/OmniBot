from __future__ import annotations

from typing import Optional

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger
from presentation.views.voice_control.member_select_view import MemberSelectView
from presentation.views.voice_control.panel_refresh import refresh_voice_control_panel
from presentation.views.voice_control.voice_invite_modal import VoiceInviteModal
from presentation.views.voice_control.voice_limit_modal import VoiceLimitModal
from presentation.views.voice_control.voice_rename_modal import VoiceRenameModal

logger = get_logger(__name__)


class VoiceControlView(disnake.ui.View):
    def __init__(self, service: VoiceServiceInterface) -> None:
        super().__init__(timeout=None)
        self.service = service

    async def _voice_channel(self, inter: disnake.MessageInteraction) -> Optional[disnake.VoiceChannel]:
        channel = inter.author.voice.channel if inter.author.voice else None
        if not channel:
            await inter.response.send_message("Вы не в голосовой комнате.", ephemeral=True)
            logger.debug("Voice action rejected because user is not in voice: user_id=%s", inter.author.id)
            return None
        return channel

    @disnake.ui.button(label="Rename", style=disnake.ButtonStyle.secondary, custom_id="voice:rename", row=0)
    async def rename_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        if await self._voice_channel(inter):
            logger.info("Voice rename button pressed: user_id=%s", inter.author.id)
            await inter.response.send_modal(VoiceRenameModal(self.service))

    @disnake.ui.button(label="Limit", style=disnake.ButtonStyle.secondary, custom_id="voice:limit", row=0)
    async def limit_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        if await self._voice_channel(inter):
            logger.info("Voice limit button pressed: user_id=%s", inter.author.id)
            await inter.response.send_modal(VoiceLimitModal(self.service))

    @disnake.ui.button(label="Lock", style=disnake.ButtonStyle.secondary, custom_id="voice:lock", row=0)
    async def lock_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        channel = await self._voice_channel(inter)
        if not channel:
            return
        try:
            await self.service.lock(channel, inter.author)
            await inter.response.send_message("Комната закрыта.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    @disnake.ui.button(label="Unlock", style=disnake.ButtonStyle.secondary, custom_id="voice:unlock", row=0)
    async def unlock_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        channel = await self._voice_channel(inter)
        if not channel:
            return
        try:
            await self.service.unlock(channel, inter.author)
            await inter.response.send_message("Комната открыта.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    @disnake.ui.button(label="Invite", style=disnake.ButtonStyle.secondary, custom_id="voice:invite", row=1)
    async def invite_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        if await self._voice_channel(inter):
            logger.info("Voice invite button pressed: user_id=%s", inter.author.id)
            await inter.response.send_modal(VoiceInviteModal(self.service))

    @disnake.ui.button(label="Kick", style=disnake.ButtonStyle.secondary, custom_id="voice:kick", row=1)
    async def kick_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        await self._send_member_action(inter, "kick")

    @disnake.ui.button(label="Ban", style=disnake.ButtonStyle.danger, custom_id="voice:ban", row=1)
    async def ban_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        await self._send_member_action(inter, "ban")

    @disnake.ui.button(label="Take admin", style=disnake.ButtonStyle.primary, custom_id="voice:claim_admin", row=2)
    async def claim_admin_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        channel = await self._voice_channel(inter)
        if not channel:
            return
        try:
            await self.service.claim_admin(channel, inter.author)
            owner = await self._room_owner(channel)
            if owner:
                await refresh_voice_control_panel(self.service, channel, owner, inter.author)
            await inter.response.send_message("Admin права получены.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    @disnake.ui.button(label="Release admin", style=disnake.ButtonStyle.secondary, custom_id="voice:release_admin", row=2)
    async def release_admin_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        channel = await self._voice_channel(inter)
        if not channel:
            return
        try:
            await self.service.release_admin(channel, inter.author)
            owner = await self._room_owner(channel)
            if owner:
                await refresh_voice_control_panel(self.service, channel, owner, None)
            await inter.response.send_message("Admin права сняты.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    @disnake.ui.button(label="Assign admin", style=disnake.ButtonStyle.secondary, custom_id="voice:assign_admin", row=2)
    async def assign_admin_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        await self._send_member_action(inter, "assign_admin")

    @disnake.ui.button(label="Clear admin", style=disnake.ButtonStyle.secondary, custom_id="voice:clear_admin", row=3)
    async def clear_admin_button(self, _button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        channel = await self._voice_channel(inter)
        if not channel:
            return
        try:
            await self.service.assign_admin(channel, None, inter.author)
            owner = await self._room_owner(channel)
            if owner:
                await refresh_voice_control_panel(self.service, channel, owner, None)
            await inter.response.send_message("Admin роль освобождена.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)

    async def _send_member_action(self, inter: disnake.MessageInteraction, action: str) -> None:
        channel = await self._voice_channel(inter)
        if not channel:
            return
        members = [member for member in channel.members if not member.bot and member.id != inter.author.id]
        if not members:
            await inter.response.send_message("Нет доступных участников.", ephemeral=True)
            return
        logger.info("Voice member action opened: action=%s channel_id=%s user_id=%s", action, channel.id, inter.author.id)
        await inter.response.send_message(
            "Выберите участника:",
            view=MemberSelectView(self.service, channel, action, members),
            ephemeral=True,
        )

    async def _room_owner(self, channel: disnake.VoiceChannel) -> Optional[disnake.Member]:
        room = await self.service._repo.get(channel.id)
        if not room:
            return None
        return channel.guild.get_member(int(room["owner_id"]))

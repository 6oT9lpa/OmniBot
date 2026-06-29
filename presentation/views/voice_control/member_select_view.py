from __future__ import annotations

from typing import List, Optional

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger
from presentation.views.voice_control.panel_refresh import refresh_voice_control_panel

logger = get_logger(__name__)


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
        options = [disnake.SelectOption(label=member.display_name[:100], value=str(member.id)) for member in members[:25]]
        menu = disnake.ui.StringSelect(placeholder="Участник", custom_id=f"voice_member:{action}", options=options)
        menu.callback = self.callback
        self.add_item(menu)

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        target = inter.guild.get_member(int(inter.data["values"][0]))
        if not target:
            await inter.response.send_message("Пользователь не найден.", ephemeral=True)
            return

        try:
            if self.action == "kick":
                await self.service.kick(self.channel, target, inter.author)
                await inter.response.send_message("Участник отключен.", ephemeral=True)
            elif self.action == "ban":
                await self.service.ban(self.channel, target, inter.author)
                await inter.response.send_message("Участник заблокирован.", ephemeral=True)
            elif self.action == "assign_admin":
                await self.service.assign_admin(self.channel, target, inter.author)
                owner = await self._room_owner()
                if owner:
                    await refresh_voice_control_panel(self.service, self.channel, owner, target)
                await inter.response.send_message("Admin передан.", ephemeral=True)
            logger.info("Voice member action completed: action=%s channel_id=%s target_id=%s", self.action, self.channel.id, target.id)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)
        except Exception as exc:
            logger.error("Member select error: %s", exc, exc_info=True)
            await inter.response.send_message("Произошла ошибка.", ephemeral=True)
        self.stop()

    async def _room_owner(self) -> Optional[disnake.Member]:
        room = await self.service._repo.get(self.channel.id)
        if not room:
            return None
        return self.channel.guild.get_member(int(room["owner_id"]))

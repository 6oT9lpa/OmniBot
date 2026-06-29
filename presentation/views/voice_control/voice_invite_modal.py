from __future__ import annotations

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VoiceInviteModal(disnake.ui.Modal):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            title="Invite user",
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
        channel = inter.author.voice.channel if inter.author.voice else None
        if not channel:
            await inter.response.send_message("Вы не в голосовой комнате.", ephemeral=True)
            return

        raw = inter.text_values["user_id"].strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            target = inter.guild.get_member(int(raw))
            if not target:
                await inter.response.send_message("Пользователь не найден.", ephemeral=True)
                return
        except ValueError:
            await inter.response.send_message("Неверный ID.", ephemeral=True)
            return

        try:
            await self.service.invite(channel, target, inter.author)
            await inter.response.send_message(f"{target.mention} приглашен.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)
        except Exception as exc:
            logger.error("Invite error: %s", exc, exc_info=True)
            await inter.response.send_message("Произошла ошибка.", ephemeral=True)

from __future__ import annotations

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VoiceRenameModal(disnake.ui.Modal):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            title="Rename room",
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
        channel = inter.author.voice.channel if inter.author.voice else None
        if not channel:
            await inter.response.send_message("Вы не в голосовой комнате.", ephemeral=True)
            return

        try:
            await self.service.rename(channel, inter.text_values["name"], inter.author)
            await inter.response.send_message("Готово.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)
        except Exception as exc:
            logger.error("Rename error: %s", exc, exc_info=True)
            await inter.response.send_message("Произошла ошибка.", ephemeral=True)

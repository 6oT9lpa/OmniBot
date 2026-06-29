from __future__ import annotations

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VoiceLimitModal(disnake.ui.Modal):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            title="Room limit",
            components=[
                disnake.ui.TextInput(
                    label="Лимит (0 - без лимита)",
                    placeholder="0",
                    custom_id="limit",
                    min_length=1,
                    max_length=2,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        channel = inter.author.voice.channel if inter.author.voice else None
        if not channel:
            await inter.response.send_message("Вы не в голосовой комнате.", ephemeral=True)
            return

        try:
            limit = int(inter.text_values["limit"])
            await self.service.set_limit(channel, limit, inter.author)
            await inter.response.send_message(f"Лимит: {limit if limit > 0 else 'без лимита'}", ephemeral=True)
        except ValueError:
            await inter.response.send_message("Введите число.", ephemeral=True)
        except PermissionError as exc:
            await inter.response.send_message(str(exc), ephemeral=True)
        except Exception as exc:
            logger.error("Limit error: %s", exc, exc_info=True)
            await inter.response.send_message("Произошла ошибка.", ephemeral=True)

from __future__ import annotations

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from infrastructure.logging import get_logger
from presentation.views.voice_control.voice_action_select_view import VoiceActionSelectView

logger = get_logger(__name__)


class VoiceControlView(disnake.ui.View):
    def __init__(self, service: VoiceServiceInterface) -> None:
        super().__init__(timeout=None)
        self.service = service
        self.add_item(VoicePanelOpenSelect(service))


class VoicePanelOpenSelect(disnake.ui.StringSelect):
    def __init__(self, service: VoiceServiceInterface) -> None:
        self.service = service
        super().__init__(
            custom_id="voice:open_controls",
            placeholder="Открыть меню управления",
            min_values=1,
            max_values=1,
            options=[
                disnake.SelectOption(
                    label="Voice controls",
                    value="open",
                    description="Показать доступные действия",
                )
            ],
        )

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        channel = inter.author.voice.channel if inter.author.voice else None
        if not channel:
            await inter.response.send_message("Вы не в голосовой комнате.", ephemeral=True)
            logger.debug("Voice controls rejected because user is not in voice: user_id=%s", inter.author.id)
            return

        room = await self.service._repo.get(channel.id)
        if not room:
            await inter.response.send_message("Это не динамическая комната OmniBot.", ephemeral=True)
            logger.debug("Voice controls rejected because room metadata missing channel_id=%s", channel.id)
            return

        view = VoiceActionSelectView(self.service, channel, room, inter.author)
        if not view.has_actions:
            await inter.response.send_message("Для вас сейчас нет доступных действий.", ephemeral=True)
            logger.debug("Voice controls empty for user_id=%s channel_id=%s", inter.author.id, channel.id)
            return

        await inter.response.send_message("Выберите действие:", view=view, ephemeral=True)
        logger.info("Voice controls opened: channel_id=%s user_id=%s", channel.id, inter.author.id)

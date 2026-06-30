from __future__ import annotations

import disnake

from core.interfaces.services.voice_service_interface import VoiceServiceInterface
from presentation.views.voice_control.voice_action_select import VoiceActionSelect


class VoiceControlView(disnake.ui.View):
    def __init__(self, service: VoiceServiceInterface) -> None:
        super().__init__(timeout=None)
        self.add_item(VoiceActionSelect(service))

from __future__ import annotations

import disnake

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RegionSelectView(disnake.ui.View):
    REGIONS = [
        ("Brazil", "brazil"),
        ("Rotterdam", "rotterdam"),
        ("India", "india"),
        ("Japan", "japan"),
        ("Singapore", "singapore"),
        ("South Africa", "southafrica"),
        ("Sydney", "sydney"),
        ("US East", "us-east"),
        ("US West", "us-west"),
        ("US Central", "us-central"),
        ("US South", "us-south"),
    ]

    def __init__(self, channel: disnake.VoiceChannel) -> None:
        super().__init__(timeout=60)
        self.channel = channel
        options = [disnake.SelectOption(label=label, value=value) for label, value in self.REGIONS]
        menu = disnake.ui.StringSelect(placeholder="Регион", custom_id="region_select", options=options[:25])
        menu.callback = self.callback
        self.add_item(menu)

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        region = inter.data["values"][0]
        if not self.channel.permissions_for(inter.author).manage_channels:
            await inter.response.send_message("Нет прав.", ephemeral=True)
            return

        try:
            await self.channel.edit(rtc_region=region)
            logger.info("Voice region changed: channel_id=%s region=%s user_id=%s", self.channel.id, region, inter.author.id)
            await inter.response.send_message(f"Регион изменен на {region}", ephemeral=True)
        except Exception as exc:
            logger.error("Failed to change region: %s", exc, exc_info=True)
            await inter.response.send_message("Ошибка при изменении региона.", ephemeral=True)
        self.stop()

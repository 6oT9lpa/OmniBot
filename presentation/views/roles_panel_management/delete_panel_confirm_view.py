from typing import Optional

import disnake

from infrastructure.logging import get_logger
from presentation.views.roles_panel_management.helpers import AdministratorOnlyView, COLOR_GREEN, COLOR_RED, COLOR_GREY

logger = get_logger(__name__)


class DeletePanelConfirmView(AdministratorOnlyView):
    def __init__(
        self,
        role_service,
        guild: disnake.Guild,
        panel: dict,
        channel: Optional[disnake.TextChannel],
        timeout: float = 60,
    ):
        super().__init__(timeout=timeout)
        self._role_service = role_service
        self._guild = guild
        self._panel = panel
        self._channel = channel

        confirm = disnake.ui.Button(
            label="Delete panel",
            style=disnake.ButtonStyle.danger,
            custom_id="delete_panel_yes",
        )
        confirm.callback = self._on_confirm
        self.add_item(confirm)

        cancel = disnake.ui.Button(
            label="Cancel",
            style=disnake.ButtonStyle.secondary,
            custom_id="delete_panel_no",
        )
        cancel.callback = self._on_cancel
        self.add_item(cancel)

    async def _on_confirm(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer()
        panel_title = self._panel.get("embed_title", "Panel")

        try:
            if self._channel:
                try:
                    msg = await self._channel.fetch_message(self._panel["message_id"])
                    await msg.delete()
                except Exception as e:
                    logger.warning(f"Could not delete panel message: {e}")

            await self._role_service.delete_panel(self._panel["message_id"])

            await interaction.edit_original_response(
                embed=disnake.Embed(
                    title="Panel deleted",
                    description=f"Panel **{panel_title}** and all its buttons have been deleted.",
                    color=COLOR_GREEN,
                ),
                view=None,
            )
            logger.info(f"Deleted panel {self._panel['message_id']}")

        except Exception as e:
            logger.error(f"Error deleting panel: {e}")
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Error", description=str(e), color=COLOR_RED), view=None
            )

    async def _on_cancel(self, interaction: disnake.MessageInteraction):
        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Deletion cancelled",
                description="The panel was not deleted",
                color=COLOR_GREY,
            ),
            view=None,
        )

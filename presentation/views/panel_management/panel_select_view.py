from typing import List, Dict, Any

import disnake

from infrastructure.logging import get_logger
from presentation.views.panel_management.helpers import panel_option_label, COLOR_ORANGE, COLOR_GREEN, COLOR_RED
from presentation.views.panel_management.panel_add_role_view import PanelAddRoleView
from presentation.views.panel_management.panel_remove_role_view import PanelRemoveRoleView
from presentation.views.panel_management.delete_panel_confirm_view import DeletePanelConfirmView

logger = get_logger(__name__)


class PanelSelectView(disnake.ui.View):
    def __init__(
        self,
        panels: List[Dict[str, Any]],
        guild: disnake.Guild,
        role_service,
        action: str,
        timeout: float = 120,
    ):
        super().__init__(timeout=timeout)
        self._panels = panels
        self._guild = guild
        self._role_service = role_service
        self._action = action

        options = []
        for panel in panels[:25]:
            label = panel_option_label(panel, guild)
            channel = guild.get_channel(panel["channel_id"])
            ch_name = f"#{channel.name}" if channel else "channel deleted"
            options.append(
                disnake.SelectOption(
                    label=label[:100],
                    value=str(panel["message_id"]),
                    description=f"{ch_name} | ID: {panel['message_id']}",
                    emoji="📋",
                )
            )

        self.panel_select = disnake.ui.StringSelect(
            custom_id="panel_select",
            placeholder="Select a panel...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.panel_select.callback = self._on_select
        self.add_item(self.panel_select)

    async def _on_select(self, interaction: disnake.MessageInteraction):
        message_id = int(interaction.data.get("values", [0])[0])
        panel = next((p for p in self._panels if p["message_id"] == message_id), None)
        if not panel:
            await interaction.response.send_message("Panel not found", ephemeral=True)
            return

        if self._action == "add":
            await self._show_add_view(interaction, panel)
        elif self._action == "remove":
            await self._show_remove_view(interaction, panel)
        elif self._action == "delete":
            await self._show_delete_view(interaction, panel)

    async def _show_add_view(self, interaction: disnake.MessageInteraction, panel: dict):
        existing_buttons = await self._role_service.get_panel_buttons(panel["message_id"])
        existing_ids = {b["role_id"] for b in existing_buttons}

        all_public = await self._role_service.get_public_roles()
        available = []
        for rd in all_public:
            if rd["role_id"] in existing_ids:
                continue
            role = self._guild.get_role(rd["role_id"])
            if not role or role.permissions.administrator or role.managed:
                continue
            if self._guild.me.top_role.position <= role.position:
                continue
            available.append(rd)

        if not available:
            await interaction.response.edit_message(
                embed=disnake.Embed(
                    title="No roles available",
                    description="All public roles are already added to this panel, or no suitable roles exist.",
                    color=COLOR_ORANGE,
                ),
                view=None,
            )
            return

        channel = self._guild.get_channel(panel["channel_id"])
        ch_name = channel.mention if channel else "deleted"
        embed = disnake.Embed(
            title="Add role",
            description=(
                f"**Panel:** {panel.get('embed_title', 'Panel')}\n"
                f"**Channel:** {ch_name}\n\n"
                "Select a role and emoji to add to the panel:"
            ),
            color=COLOR_GREEN,
        )
        view = PanelAddRoleView(
            role_service=self._role_service,
            guild=self._guild,
            panel=panel,
            available_roles=available,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def _show_remove_view(self, interaction: disnake.MessageInteraction, panel: dict):
        buttons = await self._role_service.get_panel_buttons(panel["message_id"])
        if not buttons:
            await interaction.response.edit_message(
                embed=disnake.Embed(
                    title="Panel is empty",
                    description="This panel has no buttons to remove",
                    color=COLOR_ORANGE,
                ),
                view=None,
            )
            return

        channel = self._guild.get_channel(panel["channel_id"])
        ch_name = channel.mention if channel else "deleted"
        embed = disnake.Embed(
            title="Remove role from panel",
            description=(
                f"**Panel:** {panel.get('embed_title', 'Panel')}\n"
                f"**Channel:** {ch_name}\n\n"
                "Select the role to remove.\n"
                "The role will be **removed from all members** on the server."
            ),
            color=COLOR_RED,
        )
        view = PanelRemoveRoleView(
            role_service=self._role_service,
            guild=self._guild,
            panel=panel,
            buttons=buttons,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def _show_delete_view(self, interaction: disnake.MessageInteraction, panel: dict):
        buttons = await self._role_service.get_panel_buttons(panel["message_id"])
        channel = self._guild.get_channel(panel["channel_id"])
        ch_name = channel.mention if channel else "deleted"

        embed = disnake.Embed(
            title="Confirm deletion",
            description=(
                f"**Panel:** {panel.get('embed_title', 'Panel')}\n"
                f"**Channel:** {ch_name}\n"
                f"**Roles in panel:** {len(buttons)}\n\n"
                "The panel message will be **deleted from the channel**.\n"
                "Roles will **not be removed** from members."
            ),
            color=COLOR_RED,
        )
        view = DeletePanelConfirmView(
            role_service=self._role_service,
            guild=self._guild,
            panel=panel,
            channel=channel,
        )
        await interaction.response.edit_message(embed=embed, view=view)
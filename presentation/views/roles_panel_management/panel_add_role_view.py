from typing import List, Dict, Any, Optional

import disnake

from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView
from presentation.views.roles_panel_management.helpers import rebuild_panel_embed, COLOR_GREEN, COLOR_RED, COMMON_EMOJIS

logger = get_logger(__name__)


class PanelAddRoleView(disnake.ui.View):
    def __init__(
        self,
        role_service,
        guild: disnake.Guild,
        panel: dict,
        available_roles: List[Dict[str, Any]],
        timeout: float = 120,
    ):
        super().__init__(timeout=timeout)
        self._role_service = role_service
        self._guild = guild
        self._panel = panel
        self._available_roles = available_roles
        self._selected_role_id: Optional[int] = None
        self._selected_emoji: Optional[str] = None

        role_options = []
        for rd in available_roles[:25]:
            role = guild.get_role(rd["role_id"])
            if not role:
                continue
            emoji = rd.get("display_emoji") or "🎭"
            role_options.append(
                disnake.SelectOption(
                    label=role.name[:100],
                    value=str(rd["role_id"]),
                    emoji=emoji,
                )
            )

        self.role_select = disnake.ui.StringSelect(
            custom_id="add_role_select",
            placeholder="Select a role...",
            options=role_options,
            min_values=1,
            max_values=1,
        )
        self.role_select.callback = self._on_role_select
        self.add_item(self.role_select)

        emoji_options = [
            disnake.SelectOption(label=e, value=e, emoji=e)
            for e in COMMON_EMOJIS
        ]
        self.emoji_select = disnake.ui.StringSelect(
            custom_id="add_emoji_select",
            placeholder="Select an emoji (optional)...",
            options=emoji_options,
            min_values=0,
            max_values=1,
        )
        self.emoji_select.callback = self._on_emoji_select
        self.add_item(self.emoji_select)

        self.confirm_btn = disnake.ui.Button(
            label="Add to panel",
            style=disnake.ButtonStyle.green,
            custom_id="add_confirm",
            disabled=True,
        )
        self.confirm_btn.callback = self._on_confirm
        self.add_item(self.confirm_btn)

    async def _on_role_select(self, interaction: disnake.MessageInteraction):
        self._selected_role_id = int(interaction.data.get("values", [0])[0])
        role = self._guild.get_role(self._selected_role_id)
        self.confirm_btn.disabled = False
        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Add role",
                description=(
                    f"Selected role: **{role.name if role else self._selected_role_id}**\n"
                    f"Emoji: {self._selected_emoji or '🎭 (default)'}\n\n"
                    "Select an emoji from the list or click **Add to panel**"
                ),
                color=COLOR_GREEN,
            ),
            view=self,
        )

    async def _on_emoji_select(self, interaction: disnake.MessageInteraction):
        values = interaction.data.get("values", [])
        self._selected_emoji = values[0] if values else None
        role = self._guild.get_role(self._selected_role_id) if self._selected_role_id else None
        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Add role",
                description=(
                    f"Role: **{role.name if role else '(not selected)'}**\n"
                    f"Emoji: {self._selected_emoji or '🎭 (default)'}"
                ),
                color=COLOR_GREEN,
            ),
            view=self,
        )

    async def _on_confirm(self, interaction: disnake.MessageInteraction):
        if not self._selected_role_id:
            await interaction.response.send_message("Please select a role first", ephemeral=True)
            return

        await interaction.response.defer()

        role = self._guild.get_role(self._selected_role_id)
        if not role:
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Role not found", color=COLOR_RED), view=None
            )
            return

        emoji = self._selected_emoji or "🎭"

        try:
            success = await self._role_service.add_button_to_panel(
                message_id=self._panel["message_id"],
                role_id=self._selected_role_id,
                role_name=role.name,
                emoji=emoji,
            )
            if not success:
                await interaction.edit_original_response(
                    embed=disnake.Embed(title="Panel not found", color=COLOR_RED), view=None
                )
                return

            channel = self._guild.get_channel(self._panel["channel_id"])
            if channel:
                buttons = await self._role_service.get_panel_buttons(self._panel["message_id"])
                panel_embed = await rebuild_panel_embed(self._role_service, self._guild, self._panel, buttons)
                panel_view = RolePanelView(buttons, self._panel["message_id"], self._role_service)
                try:
                    msg = await channel.fetch_message(self._panel["message_id"])
                    await msg.edit(embed=panel_embed, view=panel_view)
                except Exception as e:
                    logger.warning(f"Could not edit panel message: {e}")

            await interaction.edit_original_response(
                embed=disnake.Embed(
                    title="Role added",
                    description=f"{emoji} {role.mention} added to panel **{self._panel.get('embed_title', '')}**",
                    color=COLOR_GREEN,
                ),
                view=None,
            )
            logger.info(f"Added role {role.name} to panel {self._panel['message_id']}")

        except Exception as e:
            logger.error(f"Error adding role to panel: {e}")
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Error", description=str(e), color=COLOR_RED), view=None
            )
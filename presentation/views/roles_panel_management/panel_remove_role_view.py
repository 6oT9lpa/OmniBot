from typing import List, Dict, Any, Optional

import disnake

from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView
from presentation.views.roles_panel_management.helpers import rebuild_panel_embed, COLOR_GREEN, COLOR_RED

logger = get_logger(__name__)


class PanelRemoveRoleView(disnake.ui.View):
    def __init__(
        self,
        role_service,
        guild: disnake.Guild,
        panel: dict,
        buttons: List[Dict[str, Any]],
        timeout: float = 120,
    ):
        super().__init__(timeout=timeout)
        self._role_service = role_service
        self._guild = guild
        self._panel = panel
        self._buttons = buttons
        self._selected_role_id: Optional[int] = None

        options = []
        for btn in buttons:
            role = guild.get_role(btn["role_id"])
            if not role:
                continue
            emoji = btn.get("emoji") or "🎭"
            options.append(
                disnake.SelectOption(
                    label=role.name[:100],
                    value=str(btn["role_id"]),
                    description=f"ID: {btn['role_id']}",
                    emoji=emoji,
                )
            )

        if not options:
            options.append(disnake.SelectOption(label="No roles", value="none"))

        self.role_select = disnake.ui.StringSelect(
            custom_id="remove_role_select",
            placeholder="Select a role to remove...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.role_select.callback = self._on_role_select
        self.add_item(self.role_select)

        self.confirm_btn = disnake.ui.Button(
            label="Remove and strip role from members",
            style=disnake.ButtonStyle.danger,
            custom_id="remove_confirm",
            disabled=True,
        )
        self.confirm_btn.callback = self._on_confirm
        self.add_item(self.confirm_btn)

    async def _on_role_select(self, interaction: disnake.MessageInteraction):
        value = interaction.data.get("values", ["none"])[0]
        if value == "none":
            await interaction.response.send_message("No roles available", ephemeral=True)
            return
        self._selected_role_id = int(value)
        role = self._guild.get_role(self._selected_role_id)
        self.confirm_btn.disabled = False
        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Remove role",
                description=(
                    f"Role: **{role.name if role else self._selected_role_id}**\n\n"
                    "This role will be:\n"
                    "• Removed from the panel\n"
                    "• **Removed from all members** on the server\n\n"
                    "Click the button below to confirm."
                ),
                color=COLOR_RED,
            ),
            view=self,
        )

    async def _on_confirm(self, interaction: disnake.MessageInteraction):
        if not self._selected_role_id:
            await interaction.response.send_message("Please select a role first", ephemeral=True)
            return

        await interaction.response.defer()

        role = self._guild.get_role(self._selected_role_id)
        role_name = role.name if role else str(self._selected_role_id)

        try:
            await self._role_service.remove_button_from_panel(
                message_id=self._panel["message_id"],
                role_id=self._selected_role_id,
            )

            stripped_count = 0
            if role:
                members_with_role = [m for m in self._guild.members if role in m.roles]
                for member in members_with_role:
                    try:
                        await member.remove_roles(role, reason="Role removed from panel by administrator")
                        stripped_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove role from {member}: {e}")

            await self._update_panel_message()

            await interaction.edit_original_response(
                embed=disnake.Embed(
                    title="Role removed",
                    description=(
                        f"**{role_name}** removed from panel.\n"
                        f"Role stripped from **{stripped_count}** members."
                    ),
                    color=COLOR_GREEN,
                ),
                view=None,
            )
            logger.info(f"Removed role {role_name} from panel {self._panel['message_id']}, stripped from {stripped_count} members")

        except Exception as e:
            logger.error(f"Error removing role from panel: {e}")
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Error", description=str(e), color=COLOR_RED), view=None
            )

    async def _update_panel_message(self):
        """Обновляет embed и view/реакции панели в зависимости от режима."""
        panel = await self._role_service.get_panel(self._panel["message_id"])
        if not panel:
            return

        channel = self._guild.get_channel(panel["channel_id"])
        if not channel:
            return

        buttons = await self._role_service.get_panel_buttons(panel["message_id"])
        embed = await rebuild_panel_embed(self._role_service, self._guild, panel, buttons)

        try:
            msg = await channel.fetch_message(panel["message_id"])
        except Exception as e:
            logger.warning(f"Could not fetch panel message: {e}")
            return

        interaction_mode = panel.get("interaction_mode", "buttons")
        if interaction_mode == "reactions":
            cog = self._role_service._bot.get_cog("RolesCog") if self._role_service._bot else None
            if cog:
                if panel["message_id"] in cog._reaction_panels:
                    old_view = cog._reaction_panels.pop(panel["message_id"])
                    await old_view.clear_reactions()
                await cog.register_reaction_panel(panel["message_id"])
            await msg.edit(embed=embed, view=None)
        else:
            view = RolePanelView(buttons, panel["message_id"], self._role_service)
            await msg.edit(embed=embed, view=view)

        fingerprint = await self._role_service.ensure_panel_fingerprint(panel)
        await self._role_service.mark_panel_rendered(panel["message_id"], fingerprint)

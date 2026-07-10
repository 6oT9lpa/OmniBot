from typing import List, Dict, Any

import disnake

from infrastructure.logging import get_logger
from presentation.views.roles_panel_management.emoji_input_view import EmojiInputView
from presentation.views.roles_panel_management.helpers import AdministratorOnlyView, COLOR_BLUE

logger = get_logger(__name__)


class CreatePanelRoleSelectView(AdministratorOnlyView):
    def __init__(
        self,
        role_service,
        guild: disnake.Guild,
        available_roles: List[Dict[str, Any]],
        target_channel: disnake.TextChannel,
        embed_title: str,
        embed_description: str,
        created_by: int,
        timeout: float = 180,
    ):
        super().__init__(timeout=timeout)
        self._role_service = role_service
        self._guild = guild
        self._available_roles = available_roles
        self._target_channel = target_channel
        self._embed_title = embed_title
        self._embed_description = embed_description
        self._created_by = created_by
        self._selected_role_ids: List[int] = []

        options = []
        for rd in available_roles[:25]:
            role = guild.get_role(rd["role_id"])
            if not role:
                continue
            emoji = rd.get("display_emoji") or "🎭"
            options.append(
                disnake.SelectOption(
                    label=role.name[:100],
                    value=str(rd["role_id"]),
                    description=f"ID: {rd['role_id']}",
                    emoji=emoji,
                )
            )

        self.role_select = disnake.ui.StringSelect(
            custom_id="create_role_select",
            placeholder="Select roles for the panel...",
            options=options,
            min_values=1,
            max_values=min(len(options), 20),
        )
        self.role_select.callback = self._on_role_select
        self.add_item(self.role_select)

    async def _on_role_select(self, interaction: disnake.MessageInteraction):
        self._selected_role_ids = [int(v) for v in interaction.data.get("values", [])]

        view = EmojiInputView(
            role_service=self._role_service,
            guild=self._guild,
            selected_role_ids=self._selected_role_ids,
            available_roles=self._available_roles,
            target_channel=self._target_channel,
            embed_title=self._embed_title,
            embed_description=self._embed_description,
            created_by=self._created_by,
        )

        selected_names = []
        for rid in self._selected_role_ids:
            role = self._guild.get_role(rid)
            if role:
                selected_names.append(f"• {role.mention}")

        embed = disnake.Embed(
            title="Assign emojis to roles",
            description=(
                "Selected roles:\n" + "\n".join(selected_names) + "\n\n"
                "Select a role and assign an emoji from the list.\n"
                "This step is optional - you can skip it."
            ),
            color=COLOR_BLUE,
        )
        await interaction.response.edit_message(embed=embed, view=view)

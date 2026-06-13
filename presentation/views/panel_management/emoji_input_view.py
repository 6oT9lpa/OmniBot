from typing import List, Dict, Any, Optional

import disnake

from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView
from presentation.views.panel_management.helpers import COLOR_BLUE, COLOR_GREEN, COLOR_RED, COMMON_EMOJIS

logger = get_logger(__name__)


class EmojiInputView(disnake.ui.View):
    def __init__(
        self,
        role_service,
        guild: disnake.Guild,
        selected_role_ids: List[int],
        available_roles: List[Dict[str, Any]],
        target_channel: disnake.TextChannel,
        embed_title: str,
        embed_description: str,
        created_by: int,
        timeout: float = 300,
    ):
        super().__init__(timeout=timeout)
        self._role_service = role_service
        self._guild = guild
        self._selected_role_ids = selected_role_ids
        self._available_roles = {rd["role_id"]: rd for rd in available_roles}
        self._target_channel = target_channel
        self._embed_title = embed_title
        self._embed_description = embed_description
        self._created_by = created_by
        self._emoji_map: Dict[int, str] = {}
        for rid in selected_role_ids:
            rd = self._available_roles.get(rid, {})
            self._emoji_map[rid] = rd.get("display_emoji") or "🎭"

        role_options = []
        for rid in selected_role_ids:
            role = guild.get_role(rid)
            if role:
                role_options.append(
                    disnake.SelectOption(
                        label=role.name[:100],
                        value=str(rid),
                        emoji=self._emoji_map.get(rid, "🎭"),
                    )
                )

        self.role_picker = disnake.ui.StringSelect(
            custom_id="emoji_role_picker",
            placeholder="Select a role to assign an emoji...",
            options=role_options,
            min_values=1,
            max_values=1,
        )
        self.role_picker.callback = self._on_role_pick
        self.add_item(self.role_picker)

        emoji_options = [
            disnake.SelectOption(label=e, value=e, emoji=e)
            for e in COMMON_EMOJIS
        ]
        self.emoji_picker = disnake.ui.StringSelect(
            custom_id="emoji_picker",
            placeholder="Select an emoji for the role...",
            options=emoji_options,
            min_values=1,
            max_values=1,
        )
        self.emoji_picker.callback = self._on_emoji_pick
        self._current_role_id: Optional[int] = None
        self.add_item(self.emoji_picker)
        self._add_create_button()

    def _add_create_button(self):
        btn = disnake.ui.Button(
            label="Create panel",
            style=disnake.ButtonStyle.green,
            custom_id="create_panel_confirm",
        )
        btn.callback = self._on_create
        self.add_item(btn)

    async def _on_role_pick(self, interaction: disnake.MessageInteraction):
        self._current_role_id = int(interaction.data.get("values", [0])[0])
        role = self._guild.get_role(self._current_role_id)
        role_name = role.name if role else str(self._current_role_id)
        current_emoji = self._emoji_map.get(self._current_role_id, "🎭")
        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Assign emoji",
                description=f"Role: **{role_name}**\nCurrent emoji: {current_emoji}\n\nSelect an emoji from the list below:",
                color=COLOR_BLUE,
            ),
            view=self,
        )

    async def _on_emoji_pick(self, interaction: disnake.MessageInteraction):
        emoji = interaction.data.get("values", ["🎭"])[0]
        if self._current_role_id:
            self._emoji_map[self._current_role_id] = emoji

        role_options = []
        for rid in self._selected_role_ids:
            role = self._guild.get_role(rid)
            if role:
                current = self._emoji_map.get(rid, "🎭")
                role_options.append(
                    disnake.SelectOption(
                        label=role.name[:100],
                        value=str(rid),
                        emoji=current,
                    )
                )
        self.role_picker.options = role_options

        summary = "\n".join(
            f"{self._emoji_map.get(rid, '🎭')} <@&{rid}>"
            for rid in self._selected_role_ids
        )
        embed = disnake.Embed(
            title="Role emojis",
            description=f"Current assignments:\n{summary}\n\nYou can continue changing or click **Create panel**",
            color=COLOR_GREEN,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_create(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer()

        try:
            color_value = disnake.Color.green().value

            role_lines = []
            for rid in self._selected_role_ids:
                emoji = self._emoji_map.get(rid, "🎭")
                role_lines.append(f"{emoji}  <@&{rid}>")

            panel_embed = disnake.Embed(
                title=self._embed_title,
                description=self._embed_description,
                color=color_value,
            )
            panel_embed.add_field(
                name="Available roles",
                value="\n".join(role_lines),
                inline=False,
            )
            panel_embed.set_footer(text="Click the button to get or remove a role")

            message = await self._target_channel.send(embed=panel_embed)

            await self._role_service.create_role_panel(
                guild_id=self._guild.id,
                channel_id=self._target_channel.id,
                message_id=message.id,
                embed_title=self._embed_title,
                embed_description=self._embed_description,
                embed_color=color_value,
                created_by=self._created_by,
            )

            for rid in self._selected_role_ids:
                rd = self._available_roles.get(rid, {})
                emoji = self._emoji_map.get(rid)
                await self._role_service.add_button_to_panel(
                    message_id=message.id,
                    role_id=rid,
                    role_name=rd.get("name", str(rid)),
                    emoji=emoji,
                )

            buttons = await self._role_service.get_panel_buttons(message.id)
            if buttons:
                panel_view = RolePanelView(buttons, message.id, self._role_service)
                await message.edit(view=panel_view)

            roles_count = len(self._selected_role_ids)
            result_embed = disnake.Embed(
                title="Panel created",
                description=(
                    f"Panel **{self._embed_title}** successfully created in {self._target_channel.mention}\n\n"
                    f"Roles: **{roles_count}**\n"
                    f"Message ID: `{message.id}`\n\n"
                    f"[Go to panel](https://discord.com/channels/{self._guild.id}/{self._target_channel.id}/{message.id})"
                ),
                color=COLOR_GREEN,
            )
            await interaction.edit_original_response(embed=result_embed, view=None)
            logger.info(f"Panel created in #{self._target_channel.name} with {roles_count} roles")

        except Exception as e:
            logger.error(f"Error creating panel: {e}")
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Error", description=str(e), color=COLOR_RED),
                view=None,
            )
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
            placeholder="Выберите роль...",
            options=role_options,
            min_values=1,
            max_values=1,
        )
        self.role_select.callback = self._on_role_select
        self.add_item(self.role_select)

    def _build_emoji_select(self) -> disnake.ui.StringSelect:
        emoji_options = [
            disnake.SelectOption(label=e, value=e, emoji=e)
            for e in COMMON_EMOJIS
        ]
        select = disnake.ui.StringSelect(
            custom_id="add_emoji_select",
            placeholder="Выберите эмодзи (необязательно)...",
            options=emoji_options,
            min_values=0,
            max_values=1,
        )
        select.callback = self._on_emoji_select
        return select

    def _build_confirm_button(self) -> disnake.ui.Button:
        btn = disnake.ui.Button(
            label="Добавить на панель",
            style=disnake.ButtonStyle.green,
            custom_id="add_confirm",
        )
        btn.callback = self._on_confirm
        return btn

    def _show_step2(self):
        self.clear_items()
        self.add_item(self.role_select)

        self.emoji_select = self._build_emoji_select()
        self.add_item(self.emoji_select)

        self.confirm_btn = self._build_confirm_button()
        self.add_item(self.confirm_btn)

    async def _on_role_select(self, interaction: disnake.MessageInteraction):
        self._selected_role_id = int(interaction.data.get("values", [0])[0])
        role = self._guild.get_role(self._selected_role_id)

        self._show_step2()

        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Добавление роли",
                description=(
                    f"Выбрана роль: **{role.name if role else self._selected_role_id}**\n"
                    f"Эмодзи: {self._selected_emoji or '🎭 (по умолчанию)'}\n\n"
                    "Теперь выберите эмодзи или сразу нажмите **Добавить на панель**"
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
                title="Добавление роли",
                description=(
                    f"Роль: **{role.name if role else '(не выбрана)'}**\n"
                    f"Эмодзи: {self._selected_emoji or '🎭 (по умолчанию)'}"
                ),
                color=COLOR_GREEN,
            ),
            view=self,
        )

    async def _on_confirm(self, interaction: disnake.MessageInteraction):
        if not self._selected_role_id:
            await interaction.response.send_message("Сначала выберите роль", ephemeral=True)
            return

        await interaction.response.defer()

        role = self._guild.get_role(self._selected_role_id)
        if not role:
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Роль не найдена", color=COLOR_RED), view=None
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
                    embed=disnake.Embed(title="Панель не найдена", color=COLOR_RED), view=None
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
                    title="Роль добавлена",
                    description=f"{emoji} {role.mention} добавлена на панель **{self._panel.get('embed_title', '')}**",
                    color=COLOR_GREEN,
                ),
                view=None,
            )
            logger.info(f"Added role {role.name} to panel {self._panel['message_id']}")

        except Exception as e:
            logger.error(f"Error adding role to panel: {e}")
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Ошибка", description=str(e), color=COLOR_RED), view=None
            )
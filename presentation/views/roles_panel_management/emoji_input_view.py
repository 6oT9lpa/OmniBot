from typing import List, Dict, Any, Optional

import disnake

from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView
from presentation.views.roles_panel_management.helpers import COLOR_BLUE, COLOR_GREEN, COLOR_RED, COMMON_EMOJIS
from presentation.views.roles_panel_management.panel_mode_toggle_button import PanelModeToggleButton

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
        self._current_role_id: Optional[int] = None

        for rid in selected_role_ids[:25]:
            rd = self._available_roles.get(rid, {})
            self._emoji_map[rid] = rd.get("display_emoji") or "🎭"

        role_options = []
        for rid in selected_role_ids[:25]:
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
            placeholder="Выберите роль для назначения эмодзи...",
            options=role_options,
            min_values=1,
            max_values=1,
            row=0,
        )
        self.role_picker.callback = self._on_role_pick
        self.add_item(self.role_picker)

        emoji_options = [
            disnake.SelectOption(label=e, value=e, emoji=e)
            for e in COMMON_EMOJIS
        ]
        self.emoji_picker = disnake.ui.StringSelect(
            custom_id="emoji_picker",
            placeholder="Выберите эмодзи для роли...",
            options=emoji_options,
            min_values=1,
            max_values=1,
            row=1,
        )
        self.emoji_picker.callback = self._on_emoji_pick
        self.add_item(self.emoji_picker)

        self._mode_toggle = PanelModeToggleButton(use_reactions=False, row=2)
        self._mode_toggle.callback = self._on_toggle_mode
        self.add_item(self._mode_toggle)

        create_btn = disnake.ui.Button(
            label="Создать панель",
            style=disnake.ButtonStyle.green,
            custom_id="create_panel_confirm",
            row=2,
        )
        create_btn.callback = self._on_create
        self.add_item(create_btn)

        logger.debug(
            f"EmojiInputView created for {len(selected_role_ids)} roles "
            f"in channel #{target_channel.name}"
        )

    async def _on_toggle_mode(self, interaction: disnake.MessageInteraction):
        use_reactions = self._mode_toggle.toggle()
        mode_text = "реакции" if use_reactions else "кнопки"
        logger.debug(f"Panel mode toggled to {mode_text} by {interaction.author}")

        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Режим панели изменён",
                description=(
                    f"Панель будет использовать **{mode_text}**.\n\n"
                    "Режим реакций: пользователи кликают на реакции под сообщением.\n"
                    "Режим кнопок: пользователи кликают на интерактивные кнопки."
                ),
                color=COLOR_GREEN if use_reactions else COLOR_BLUE,
            ),
            view=self,
        )

    async def _on_role_pick(self, interaction: disnake.MessageInteraction):
        self._current_role_id = int(interaction.data.get("values", [0])[0])
        role = self._guild.get_role(self._current_role_id)
        role_name = role.name if role else str(self._current_role_id)
        current_emoji = self._emoji_map.get(self._current_role_id, "🎭")

        logger.debug(f"Role selected for emoji assignment: {role_name}")

        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Назначить эмодзи",
                description=(
                    f"Роль: **{role_name}**\n"
                    f"Текущий эмодзи: {current_emoji}\n\n"
                    "Выберите эмодзи из списка ниже:"
                ),
                color=COLOR_BLUE,
            ),
            view=self,
        )

    async def _on_emoji_pick(self, interaction: disnake.MessageInteraction):
        emoji = interaction.data.get("values", ["🎭"])[0]
        if self._current_role_id:
            self._emoji_map[self._current_role_id] = emoji
            logger.debug(
                f"Emoji {emoji} assigned to role {self._current_role_id}"
            )

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

        mode_text = "реакции" if self._mode_toggle.use_reactions else "кнопки"
        summary = "\n".join(
            f"{self._emoji_map.get(rid, '🎭')} <@&{rid}>"
            for rid in self._selected_role_ids
        )
        await interaction.response.edit_message(
            embed=disnake.Embed(
                title="Эмодзи ролей",
                description=(
                    f"Текущие назначения:\n{summary}\n\n"
                    f"Тип панели: **{mode_text}**\n\n"
                    "Можно продолжить изменять или нажать **Создать панель**"
                ),
                color=COLOR_GREEN,
            ),
            view=self,
        )

    async def _on_create(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer()
        logger.info(
            f"Creating panel '{self._embed_title}' "
            f"in #{self._target_channel.name} by {interaction.author}"
        )

        from presentation.views.roles_panel_management.role_panel_reaction_view import RolePanelReactionView

        try:
            color_value = disnake.Color.green().value

            role_lines = [
                f"{self._emoji_map.get(rid, '🎭')}  <@&{rid}>"
                for rid in self._selected_role_ids
            ]

            panel_embed = disnake.Embed(
                title=self._embed_title,
                description=self._embed_description,
                color=color_value,
            )
            panel_embed.add_field(
                name="Доступные роли",
                value="\n".join(role_lines),
                inline=False,
            )

            use_reactions = self._mode_toggle.use_reactions
            if use_reactions:
                panel_embed.set_footer(
                    text="Нажмите на реакцию под этим сообщением, чтобы получить или снять роль"
                )
            else:
                panel_embed.set_footer(
                    text="Нажмите на кнопку ниже, чтобы получить или снять роль"
                )

            message = await self._target_channel.send(embed=panel_embed)
            logger.debug(f"Panel message sent: {message.id}")

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

            if use_reactions:
                reaction_view = RolePanelReactionView(message, buttons, self._role_service)
                await reaction_view.setup()
                await message.edit(view=None)
                logger.info(
                    f"Created reaction panel '{self._embed_title}' "
                    f"in #{self._target_channel.name}, message {message.id}"
                )
            else:
                if buttons:
                    panel_view = RolePanelView(buttons, message.id, self._role_service)
                    await message.edit(view=panel_view)
                logger.info(
                    f"Created button panel '{self._embed_title}' "
                    f"in #{self._target_channel.name}, message {message.id}"
                )

            roles_count = len(self._selected_role_ids)
            panel_type = "реакции" if use_reactions else "кнопки"
            result_embed = disnake.Embed(
                title="Панель создана",
                description=(
                    f"Панель **{self._embed_title}** успешно создана в {self._target_channel.mention}\n\n"
                    f"Тип панели: **{panel_type}**\n"
                    f"Ролей: **{roles_count}**\n"
                    f"ID сообщения: `{message.id}`\n\n"
                    f"[Перейти к панели]"
                    f"(https://discord.com/channels/{self._guild.id}"
                    f"/{self._target_channel.id}/{message.id})"
                ),
                color=COLOR_GREEN,
            )
            await interaction.edit_original_response(embed=result_embed, view=None)

        except Exception as e:
            logger.error(f"Error creating panel '{self._embed_title}': {e}")
            await interaction.edit_original_response(
                embed=disnake.Embed(
                    title="Ошибка",
                    description=str(e),
                    color=COLOR_RED,
                ),
                view=None,
            )
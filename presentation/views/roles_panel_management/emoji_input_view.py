from typing import List, Dict, Any, Optional

import disnake

from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView
from presentation.views.roles_panel_management.helpers import COLOR_BLUE, COLOR_GREEN, COLOR_RED, COMMON_EMOJIS, MAX_PANEL_ITEMS, get_emoji_select_options
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
        self._selected_role_ids = selected_role_ids[:MAX_PANEL_ITEMS]
        # Словарь {role_id: role_dict} для быстрого доступа к данным роли
        self._available_roles = {rd["role_id"]: rd for rd in available_roles}
        self._target_channel = target_channel
        self._embed_title = embed_title
        self._embed_description = embed_description
        self._created_by = created_by
        self._emoji_map: Dict[int, str] = {}
        self._current_role_id: Optional[int] = None

        # Инициализация карты эмодзи с защитой от неверных данных
        for rid in self._selected_role_ids:
            rd = self._available_roles.get(rid)
            if rd and isinstance(rd, dict):
                default_emoji = rd.get("display_emoji") or "🎭"
            else:
                default_emoji = "🎭"
            self._emoji_map[rid] = default_emoji

        self._rebuild_role_options()

        self.role_picker = disnake.ui.StringSelect(
            custom_id="emoji_role_picker",
            placeholder="Выберите роль для назначения эмодзи...",
            options=self._role_options,
            min_values=1,
            max_values=1,
            row=0,
        )
        self.role_picker.callback = self._on_role_pick
        self.add_item(self.role_picker)

        emoji_options = get_emoji_select_options(self._guild)
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
            "EmojiInputView created for %s roles in channel id=%s",
            len(self._selected_role_ids),
            target_channel.id,
        )

    def _rebuild_role_options(self) -> None:
        self._role_options = []
        for rid in self._selected_role_ids:
            role = self._guild.get_role(rid)
            if role:
                current = self._emoji_map.get(rid, "🎭")
                self._role_options.append(
                    disnake.SelectOption(
                        label=role.name[:100],
                        value=str(rid),
                        emoji=current,
                    )
                )

    def _build_summary_embed(self, title: str, color: int) -> disnake.Embed:
        mode_text = "реакции" if self._mode_toggle.use_reactions else "кнопки"
        summary = "\n".join(
            f"{self._emoji_map.get(rid, '🎭')} <@&{rid}>"
            for rid in self._selected_role_ids
        ) or "Роли ещё не выбраны"
        return disnake.Embed(
            title=title,
            description=(
                f"Текущие назначения:\n{summary}\n\n"
                f"Тип панели: **{mode_text}**\n\n"
                "Можно продолжить изменять или нажать **Создать панель**"
            ),
            color=color,
        )

    async def _on_toggle_mode(self, interaction: disnake.MessageInteraction):
        use_reactions = self._mode_toggle.toggle()
        mode_text = "реакции" if use_reactions else "кнопки"
        logger.debug("Panel mode toggled to %s by user id=%s", mode_text, interaction.author.id)

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

        logger.debug("Role id=%s selected for emoji assignment", self._current_role_id)

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
            logger.debug("Emoji %s assigned to role id=%s", emoji, self._current_role_id)

        self._rebuild_role_options()
        await interaction.response.edit_message(
            embed=self._build_summary_embed("Эмодзи ролей", COLOR_GREEN),
            view=self,
        )

    async def _on_create(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer()
        logger.info(
            "Creating panel '%s' in channel id=%s by user id=%s",
            self._embed_title,
            self._target_channel.id,
            interaction.author.id,
        )

        from presentation.views.roles_panel_management.role_panel_reaction_view import RolePanelReactionView

        try:
            if len(self._selected_role_ids) > MAX_PANEL_ITEMS:
                raise ValueError(f"Panel cannot contain more than {MAX_PANEL_ITEMS} buttons or reactions")

            color_value = disnake.Color.green().value
            visible_role_ids = self._selected_role_ids[:MAX_PANEL_ITEMS]

            role_lines = [
                f"{self._emoji_map.get(rid, '🎭')}  <@&{rid}>"
                for rid in visible_role_ids
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
            logger.debug("Panel message sent: %s", message.id)

            await self._role_service.create_role_panel(
                guild_id=self._guild.id,
                channel_id=self._target_channel.id,
                message_id=message.id,
                embed_title=self._embed_title,
                embed_description=self._embed_description,
                embed_color=color_value,
                created_by=self._created_by,
                interaction_mode="reactions" if use_reactions else "buttons",
            )

            for rid in visible_role_ids:
                role = self._guild.get_role(rid)
                role_name = role.name if role else str(rid)
                emoji = self._emoji_map.get(rid)
                await self._role_service.add_button_to_panel(
                    message_id=message.id,
                    role_id=rid,
                    role_name=role_name,
                    emoji=emoji,
                )

            buttons = await self._role_service.get_panel_buttons(message.id)

            if use_reactions:
                reaction_view = RolePanelReactionView(message, buttons, self._role_service)
                await reaction_view.setup()
                await message.edit(view=None)
                cog = self._role_service._bot.get_cog("RolesCog") if self._role_service._bot else None
                if cog:
                    await cog.register_reaction_panel(message.id)
                logger.info(
                    "Created reaction panel '%s' in channel id=%s, message id=%s",
                    self._embed_title,
                    self._target_channel.id,
                    message.id,
                )
            else:
                if buttons:
                    panel_view = RolePanelView(buttons, message.id, self._role_service)
                    await message.edit(view=panel_view)
                logger.info(
                    "Created button panel '%s' in channel id=%s, message id=%s",
                    self._embed_title,
                    self._target_channel.id,
                    message.id,
                )

            panel = await self._role_service.get_panel(message.id)
            if panel:
                fingerprint = await self._role_service.ensure_panel_fingerprint(panel)
                await self._role_service.mark_panel_rendered(message.id, fingerprint)

            roles_count = len(visible_role_ids)
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

        except Exception as exc:
            logger.error("Error creating panel '%s': %s", self._embed_title, exc)
            await interaction.edit_original_response(
                embed=disnake.Embed(
                    title="Ошибка",
                    description=str(exc),
                    color=COLOR_RED,
                ),
                view=None,
            )

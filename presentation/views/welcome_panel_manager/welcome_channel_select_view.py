import disnake
from typing import Optional

from application.services.welcome_service import WelcomeService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class WelcomeChannelSelectView(disnake.ui.View):
    def __init__(
        self,
        welcome_service: WelcomeService,
        guild: disnake.Guild,
        current_config: dict,
        timeout: float = 180,
    ):
        super().__init__(timeout=timeout)
        self._welcome_service = welcome_service
        self._guild = guild
        self._guild_id = guild.id
        self._rules_channel_id = current_config.get("rules_channel_id")
        self._roles_channel_id = current_config.get("roles_channel_id")

        rules_options = self._build_channel_options(self._rules_channel_id)
        self.rules_select = disnake.ui.StringSelect(
            custom_id="welcome_rules_select",
            placeholder="Выберите канал с правилами",
            options=rules_options,
            min_values=0, 
            max_values=1,
            row=0,
        )
        self.rules_select.callback = self._on_rules_select
        self.add_item(self.rules_select)

        roles_options = self._build_channel_options(self._roles_channel_id)
        self.roles_select = disnake.ui.StringSelect(
            custom_id="welcome_roles_select",
            placeholder="Выберите канал для выдачи ролей",
            options=roles_options,
            min_values=0,
            max_values=1,
            row=1,
        )
        self.roles_select.callback = self._on_roles_select
        self.add_item(self.roles_select)

        save_btn = disnake.ui.Button(
            label="Сохранить",
            style=disnake.ButtonStyle.green,
            custom_id="save_channels",
            row=2,
        )
        save_btn.callback = self._on_save
        self.add_item(save_btn)

    def _build_channel_options(self, current_id: Optional[int]) -> list:
        """Создаёт список опций из текстовых каналов сервера"""

        options = []
        options.append(
            disnake.SelectOption(
                label="Не использовать",
                value="none",
                default=current_id is None,
                emoji="🚫"
            )
        )
        for channel in self._guild.text_channels:
            if not channel.permissions_for(self._guild.me).send_messages:
                continue
            options.append(
                disnake.SelectOption(
                    label=f"#{channel.name}",
                    value=str(channel.id),
                    default=channel.id == current_id,
                    description=f"ID: {channel.id}" if len(channel.name) < 80 else None,
                )
            )
        return options

    async def _on_rules_select(self, interaction: disnake.MessageInteraction):
        value = interaction.data.get("values", ["none"])[0]
        self._rules_channel_id = int(value) if value != "none" else None
        await interaction.response.edit_message(view=self)

    async def _on_roles_select(self, interaction: disnake.MessageInteraction):
        value = interaction.data.get("values", ["none"])[0]
        self._roles_channel_id = int(value) if value != "none" else None
        await interaction.response.edit_message(view=self)

    async def _on_save(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer(ephemeral=True)
        try:
            await self._welcome_service.update_config(
                guild_id=self._guild_id,
                rules_channel_id=self._rules_channel_id,
                roles_channel_id=self._roles_channel_id,
            )
            
            embed = disnake.Embed(
                title="Каналы настроены",
                description="Выберите каналы для правил и ролей.\n"
                            "В описании приветствия используйте `{rules}` и `{roles}` для автоматической ссылки.",
                color=0x57F287,
            )

            if self._rules_channel_id:
                ch = self._guild.get_channel(self._rules_channel_id)
                embed.add_field(name="Канал правил", value=ch.mention if ch else "Удалён", inline=True)
            if self._roles_channel_id:
                ch = self._guild.get_channel(self._roles_channel_id)
                embed.add_field(name="Канал ролей", value=ch.mention if ch else "Удалён", inline=True)

            await interaction.edit_original_response(embed=embed, view=None)
            logger.info(f"Welcome channels updated for guild {self._guild_id}")

        except Exception as e:
            logger.error(f"Error saving channels: {e}", exc_info=True)
            await interaction.edit_original_response(
                embed=disnake.Embed(title="Ошибка", description=str(e), color=0xED4245),
                view=None,
            )
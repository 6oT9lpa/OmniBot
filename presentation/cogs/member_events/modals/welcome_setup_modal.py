import disnake
import re
from disnake.ui import Modal, TextInput

from application.services.welcome_service import WelcomeService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class WelcomeSetupModal(Modal):
    def __init__(self, welcome_service: WelcomeService, guild_id: int, current_config: dict):
        self._welcome_service = welcome_service
        self._guild_id = guild_id

        title = current_config.get("title", "Добро пожаловать!")
        description = current_config.get("description", "")
        color = current_config.get("color", 0x57F287)
        placeholder_text = (
            "Доступные переменные: {user}, {guild}, {member_count}, "
            "{rules}, {roles} - подробнее в документации"
        )

        components = [
            TextInput(
                label="Заголовок",
                placeholder="Введите заголовок приветственного сообщения",
                value=title,
                max_length=256,
                required=False,
                custom_id="welcome_title"
            ),
            TextInput(
                label="Описание",
                placeholder=placeholder_text[:100],
                value=description,
                max_length=2000,
                required=False,
                custom_id="welcome_description",
                style=disnake.TextInputStyle.paragraph
            ),
            TextInput(
                label="Цвет (HEX)",
                placeholder="#57F287",
                value=f"#{color:06X}",
                max_length=7,
                required=False,
                custom_id="welcome_color"
            )
        ]

        super().__init__(
            title="Настройка приветствия (часть 1)",
            custom_id="welcome_setup_modal",
            components=components,
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            logger.info(f"Processing welcome setup modal for guild {self._guild_id}")

            title = interaction.text_values.get("welcome_title", "")
            description = interaction.text_values.get("welcome_description", "")
            color_hex = interaction.text_values.get("welcome_color", "#57F287")

            hex_pattern = re.compile(r'^#?([A-Fa-f0-9]{6})$')
            match = hex_pattern.match(color_hex)
            if not match:
                await interaction.response.send_message(
                    "Неверный формат цвета. Используйте HEX (например, #57F287 или 57F287).",
                    ephemeral=True
                )
                return

            color_value = int(match.group(1), 16)

            await self._welcome_service.update_config(
                guild_id=self._guild_id,
                title=title,
                description=description,
                color=color_value,
            )

            embed = disnake.Embed(
                title="Настройки приветствия сохранены",
                description="Конфигурация приветственного сообщения обновлена",
                color=color_value
            )
            
            embed.add_field(name="Заголовок", value=title or "Стандартный", inline=False)
            
            desc_preview = description[:100] + "..." if description and len(description) > 100 else description or "Стандартное"
            embed.add_field(name="Описание", value=desc_preview, inline=False)
            embed.add_field(name="Цвет", value=color_hex, inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Welcome config updated successfully for guild {self._guild_id}")

        except Exception as e:
            logger.error(f"Error saving welcome config for guild {self._guild_id}: {e}", exc_info=True)
            await interaction.response.send_message(
                f"Ошибка при сохранении настроек: {e}",
                ephemeral=True
            )
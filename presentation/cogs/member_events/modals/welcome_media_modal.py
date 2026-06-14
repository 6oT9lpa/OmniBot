import disnake
from disnake.ui import Modal, TextInput

from application.services.welcome_service import WelcomeService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class WelcomeMediaModal(Modal):
    def __init__(self, welcome_service: WelcomeService, guild_id: int, current_config: dict):
        self._welcome_service = welcome_service
        self._guild_id = guild_id

        footer_text = current_config.get("footer_text", "")
        footer_icon_url = current_config.get("footer_icon_url", "")
        thumbnail_url = current_config.get("thumbnail_url", "")

        components = [
            TextInput(
                label="Миниатюра (URL)",
                placeholder="https://example.com/image.png",
                value=thumbnail_url if thumbnail_url else "",
                max_length=500,
                required=False,
                custom_id="welcome_thumbnail"
            ),
            TextInput(
                label="Нижний колонтитул (текст)",
                placeholder="Текст внизу сообщения",
                value=footer_text if footer_text else "",
                max_length=200,
                required=False,
                custom_id="welcome_footer_text"
            ),
            TextInput(
                label="Иконка колонтитула (URL)",
                placeholder="https://example.com/icon.png",
                value=footer_icon_url if footer_icon_url else "",
                max_length=500,
                required=False,
                custom_id="welcome_footer_icon"
            )
        ]

        super().__init__(
            title="Настройка приветствия (часть 2)",
            custom_id="welcome_media_modal",
            components=components,
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        try:
            logger.info(f"Processing welcome media modal for guild {self._guild_id}")
            
            thumbnail_url = interaction.text_values.get("welcome_thumbnail", "") or None
            footer_text = interaction.text_values.get("welcome_footer_text", "") or None
            footer_icon_url = interaction.text_values.get("welcome_footer_icon", "") or None
            
            thumbnail_url = thumbnail_url if thumbnail_url else None
            footer_text = footer_text if footer_text else None
            footer_icon_url = footer_icon_url if footer_icon_url else None
            
            logger.debug(f"Полученные данные: thumbnail_url={thumbnail_url!r}, footer_text={footer_text!r}, footer_icon_url={footer_icon_url!r}")

            await self._welcome_service.update_config(
                guild_id=self._guild_id,
                thumbnail_url=thumbnail_url,
                footer_text=footer_text,
                footer_icon_url=footer_icon_url,
            )

            embed = disnake.Embed(
                title="Настройки приветствия сохранены",
                description="Медиа-конфигурация приветственного сообщения обновлена",
                color=0x57F287
            )
            
            if footer_text:
                embed.add_field(name="Колонтитул", value=footer_text, inline=False)
            
            if thumbnail_url:
                embed.add_field(name="Миниатюра", value="[Ссылка](" + thumbnail_url + ")", inline=True)
                
            if footer_icon_url:
                embed.add_field(name="Иконка колонтитула", value="[Ссылка](" + footer_icon_url + ")", inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Welcome media config updated for guild {self._guild_id}")

        except Exception as e:
            logger.error(f"Error saving welcome media config for guild {self._guild_id}: {e}", exc_info=True)
            await interaction.response.send_message(
                f"Ошибка при сохранении настроек: {e}",
                ephemeral=True
            )
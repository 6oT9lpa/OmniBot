import disnake
from typing import Optional, List, Dict, Any, Union, Tuple

from infrastructure.logging import get_logger

logger = get_logger(__name__)


DEFAULT_COLORS = {
    "moderation": 0xED4245,
    "warn": 0xFEE75C,
    "info": 0x5865F2,
    "success": 0x57F287,
    "voice": 0x5865F2,
    "message": 0x5865F2,
}

MAX_IMAGES = 10


class EmbedField:
    def __init__(
        self,
        name: str,
        value: str,
        *,
        inline: bool = True,
    ):
        if not name:
            logger.info("[EmbedBuilder] Field name must not be empty")
            raise
        if not value:
            logger.info("[EmbedBuilder] Field value must not be empty")
            raise
        
        self.name = name
        self.value = value
        self.inline = inline


class ImageCarouselView(disnake.ui.View):
    def __init__(self, embed: disnake.Embed, images: List[str], start_index: int = 0):
        super().__init__(timeout=180)
        self._base_embed = embed
        self.images = images
        self.current_index = start_index
        self._update_buttons()

    def _update_buttons(self):
        """Активирует/деактивирует кнопки в зависимости от текущего индекса."""

        self.previous_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index == len(self.images) - 1

    async def _update_message(self, interaction: disnake.MessageInteraction):
        """Создаёт новое embed с текущим изображением и редактирует сообщение."""

        new_embed = disnake.Embed.from_dict(self._base_embed.to_dict())
        new_embed.set_image(url=self.images[self.current_index])
        self._update_buttons()
        await interaction.response.edit_message(embed=new_embed, view=self)

    @disnake.ui.button(label="◀", style=disnake.ButtonStyle.secondary)
    async def previous_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.current_index -= 1
        await self._update_message(interaction)

    @disnake.ui.button(label="▶", style=disnake.ButtonStyle.secondary)
    async def next_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.current_index += 1
        await self._update_message(interaction)


class EmbedBuilder:
    def __init__(self, color: int = DEFAULT_COLORS["info"]):
        self._embed = disnake.Embed(color=color, timestamp=disnake.utils.utcnow())
        self._fields: List[EmbedField] = []
        self._images: List[str] = []

    def set_title(self, title: str) -> "EmbedBuilder":
        if not title:
            raise ValueError("Title must not be empty")
        self._embed.title = title
        return self

    def set_description(self, description: str) -> "EmbedBuilder":
        if not description:
            raise ValueError("Description must not be empty")
        self._embed.description = description
        return self

    def set_color(self, color: int) -> "EmbedBuilder":
        self._embed.color = color
        return self

    def set_author(self, name: str, *, icon_url: Optional[str] = None) -> "EmbedBuilder":
        self._embed.set_author(name=name, icon_url=icon_url)
        return self

    def set_footer(self, text: str, *, icon_url: Optional[str] = None) -> "EmbedBuilder":
        self._embed.set_footer(text=text, icon_url=icon_url)
        return self

    def add_field(self, name: str, value: str, *, inline: bool = True) -> "EmbedBuilder":
        self._fields.append(EmbedField(name=name, value=value, inline=inline))
        return self

    def set_thumbnail(self, url: str) -> "EmbedBuilder":
        self._embed.set_thumbnail(url=url)
        return self

    def add_fields(self, *fields: Union[EmbedField, tuple]) -> "EmbedBuilder":
        for field in fields:
            if isinstance(field, EmbedField):
                self._fields.append(field)
            elif isinstance(field, tuple) and len(field) == 2:
                self._fields.append(EmbedField(name=field[0], value=field[1]))
            else:
                raise ValueError(f"Invalid field: {field}")
        return self

    def add_image(self, url: str) -> "EmbedBuilder":
        """Добавляет изображение в галерею"""
        if len(self._images) >= MAX_IMAGES:
            raise ValueError(f"Нельзя добавить больше {MAX_IMAGES} изображений")
        self._images.append(url)
        return self

    def set_images(self, urls: List[str]) -> "EmbedBuilder":
        """Заменяет список изображений"""
        if len(urls) > MAX_IMAGES:
            raise ValueError(f"Максимум {MAX_IMAGES} изображений")
        self._images = list(urls)
        return self

    def build(self) -> disnake.Embed:
        """Собирает embed с 0–1 изображением (первое из списка)."""
        for field in self._fields:
            self._embed.add_field(name=field.name, value=field.value, inline=field.inline)

        if self._images:
            self._embed.set_image(url=self._images[0])

        return self._embed

    def build_with_view(self) -> Tuple[disnake.Embed, disnake.ui.View]:
        """Собирает embed с первым изображением и View для переключения."""
        if not self._images:
            raise ValueError("Нужно хотя бы одно изображение для build_with_view")

        embed = self.build()
        view = ImageCarouselView(embed, self._images, start_index=0)
        return embed, view

    def build_auto(self) -> Dict[str, Any]:
        """Автоматический выбор режима"""
        if len(self._images) <= 1:
            return {"embed": self.build()}
        else:
            embed, view = self.build_with_view()
            return {"embed": embed, "view": view}
import disnake
from typing import Optional, List, Dict, Any, Union


DEFAULT_COLORS = {
    "moderation": 0xED4245,
    "warn": 0xFEE75C,
    "info": 0x5865F2,
    "success": 0x57F287,
    "voice": 0x5865F2,
    "message": 0x5865F2,
}


class EmbedField:
    def __init__(
        self,
        name: str,
        value: str,
        *,
        inline: bool = True,
    ):
        if not name:
            raise ValueError("Field name must not be empty")
        if not value:
            raise ValueError("Field value must not be empty")
        self.name = name
        self.value = value
        self.inline = inline


class EmbedBuilder:
    def __init__(self, color: int = DEFAULT_COLORS["info"]):
        self._embed = disnake.Embed(color=color, timestamp=disnake.utils.utcnow())
        self._fields: List[EmbedField] = []

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

    def build(self) -> disnake.Embed:
        for field in self._fields:
            self._embed.add_field(name=field.name, value=field.value, inline=field.inline)
        return self._embed

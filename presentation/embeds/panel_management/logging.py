import disnake
from typing import Union

from presentation.embeds.panel_management.base import EmbedBuilder


class VoiceLogEmbedBuilder:
    @staticmethod
    def build_join(member: disnake.Member, channel_name: str) -> disnake.Embed:
        builder = EmbedBuilder(color=0x57F287)
        builder.set_title(f"{member} ({member.id})")
        builder.add_field("Channel:", channel_name)
        return builder.build()

    @staticmethod
    def build_leave(member: disnake.Member, channel_name: str) -> disnake.Embed:
        builder = EmbedBuilder(color=0xED4245)
        builder.set_title(f"{member} ({member.id})")
        builder.add_field("Channel:", channel_name)
        return builder.build()

    @staticmethod
    def build_move(member: disnake.Member, before_channel: str, after_channel: str) -> disnake.Embed:
        builder = EmbedBuilder(color=0x5865F2)
        builder.set_title(f"{member} ({member.id})")
        builder.add_field("Before Channel:", before_channel)
        builder.add_field("After Channel:", after_channel)
        return builder.build()


class MessageLogEmbedBuilder:
    @staticmethod
    def build_delete(author: Union[disnake.User, disnake.Member]) -> disnake.Embed:
        builder = EmbedBuilder(color=0xED4245)
        builder.set_title(f"{author} ({author.id})")
        return builder.build()

    @staticmethod
    def build_edit(author: Union[disnake.User, disnake.Member]) -> disnake.Embed:
        builder = EmbedBuilder(color=0xFEE75C)
        builder.set_title(f"{author} ({author.id})")
        return builder.build()
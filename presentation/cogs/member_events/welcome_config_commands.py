import disnake
from disnake.ext import commands

from application.services.welcome_service import WelcomeService
from infrastructure.logging import get_logger
from presentation.cogs.member_events.modals import (
    WelcomeSetupModal,
    WelcomeMediaModal
)
from presentation.views.welcome_panel_manager import WelcomeChannelSelectView
from presentation.views.roles_panel_management.helpers import COLOR_GREEN, COLOR_RED, COLOR_BLUE

logger = get_logger(__name__)


class WelcomeConfigCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, welcome_service: WelcomeService):
        self._bot = bot
        self._welcome_service = welcome_service
        logger.info("WelcomeConfigCommands initialized")

    @commands.slash_command(
        name="welcome",
        description="Настройка приветственного сообщения"
    )
    async def welcome_group(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @welcome_group.sub_command(
        name="setup",
        description="Открыть панель настройки приветственного сообщения (основное)"
    )
    async def setup_welcome(
        self,
        ctx: disnake.ApplicationCommandInteraction
    ):
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"Non-admin {ctx.author} attempted to use welcome setup in guild {ctx.guild.id}")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            logger.info(f"User {ctx.author} opened welcome setup modal for guild {ctx.guild.id}")
            config = await self._welcome_service.get_config(ctx.guild.id) or {}
            
            modal = WelcomeSetupModal(self._welcome_service, ctx.guild.id, config)
            await ctx.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in setup_welcome command for guild {ctx.guild.id}: {e}", exc_info=True)
            await ctx.response.send_message(
                "Произошла ошибка при открытии панели настроек",
                ephemeral=True
            )

    @welcome_group.sub_command(
        name="media",
        description="Настройка медиа (миниатюра, колонтитул)"
    )
    async def setup_media(
        self,
        ctx: disnake.ApplicationCommandInteraction
    ):
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"Non-admin {ctx.author} attempted to use welcome media in guild {ctx.guild.id}")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            logger.info(f"User {ctx.author} opened welcome media modal for guild {ctx.guild.id}")
            config = await self._welcome_service.get_config(ctx.guild.id) or {}
            
            modal = WelcomeMediaModal(self._welcome_service, ctx.guild.id, config)
            await ctx.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in setup_media command for guild {ctx.guild.id}: {e}", exc_info=True)
            await ctx.response.send_message(
                "Произошла ошибка при открытии панели настроек",
                ephemeral=True
            )

    @welcome_group.sub_command(
        name="channels",
        description="Настройка каналов для правил и ролей (выбор из списка)"
    )
    async def setup_channels(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            config = await self._welcome_service.get_config(ctx.guild.id) or {}
            view = WelcomeChannelSelectView(
                welcome_service=self._welcome_service,
                guild=ctx.guild,
                current_config=config,
            )
            embed = disnake.Embed(
                title="Настройка каналов для приветствия",
                description="Выберите каналы, на которые будут ссылаться переменные **{rules}** и **{roles}** в описании приветствия.",
                color=0x5865F2,
            )
            await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error opening channel selector: {e}", exc_info=True)
            await ctx.response.send_message("Ошибка при открытии панели выбора каналов", ephemeral=True)

    @welcome_group.sub_command(
        name="toggle",
        description="Включить или выключить приветственное сообщение"
    )
    async def toggle_welcome(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        enabled: bool = commands.Param(description="Включить или выключить")
    ):
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"Non-admin {ctx.author} attempted to toggle welcome in guild {ctx.guild.id}")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            logger.info(f"User {ctx.author} toggled welcome to {enabled} for guild {ctx.guild.id}")
            await self._welcome_service.set_enabled(ctx.guild.id, enabled)
            status = "включено" if enabled else "выключено"

            embed = disnake.Embed(
                title="Приветственное сообщение",
                description=f"Приветствие {status}",
                color=COLOR_GREEN if enabled else COLOR_RED
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error toggling welcome for guild {ctx.guild.id}: {e}", exc_info=True)
            await ctx.response.send_message(
                "Произошла ошибка при изменении настроек",
                ephemeral=True
            )

    @welcome_group.sub_command(
        name="preview",
        description="Показать предпросмотр приветственного сообщения"
    )
    async def preview_welcome(
        self,
        ctx: disnake.ApplicationCommandInteraction
    ):
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"Non-admin {ctx.author} attempted to preview welcome in guild {ctx.guild.id}")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            logger.info(f"User {ctx.author} requested welcome preview for guild {ctx.guild.id}")
            config = await self._welcome_service.get_config(ctx.guild.id)
            embed = self._welcome_service.build_embed(ctx.author, config)
            view = await self._welcome_service.get_welcome_buttons(ctx.guild)

            await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in preview_welcome for guild {ctx.guild.id}: {e}", exc_info=True)
            await ctx.response.send_message(
                "Произошла ошибка при создании предпросмотра",
                ephemeral=True
            )

    @welcome_group.sub_command(
        name="reset",
        description="Сбросить настройки приветствия на стандартные"
    )
    async def reset_welcome(
        self,
        ctx: disnake.ApplicationCommandInteraction
    ):
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"Non-admin {ctx.author} attempted to reset welcome in guild {ctx.guild.id}")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            logger.info(f"User {ctx.author} reset welcome config for guild {ctx.guild.id}")
            await self._welcome_service.reset_config(ctx.guild.id)

            embed = disnake.Embed(
                title="Настройки сброшены",
                description="Приветственное сообщение сброшено до стандартных настроек",
                color=COLOR_GREEN
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error resetting welcome for guild {ctx.guild.id}: {e}", exc_info=True)
            await ctx.response.send_message(
                "Произошла ошибка при сбросе настроек",
                ephemeral=True
            )

    @welcome_group.sub_command(
        name="show",
        description="Показать текущие настройки приветствия"
    )
    async def show_config(
        self,
        ctx: disnake.ApplicationCommandInteraction
    ):
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"Non-admin {ctx.author} attempted to show welcome config in guild {ctx.guild.id}")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        try:
            logger.info(f"User {ctx.author} requested welcome config for guild {ctx.guild.id}")
            config = await self._welcome_service.get_config(ctx.guild.id)

            if not config:
                await ctx.response.send_message("Используются стандартные настройки. Используйте `/welcome setup` для настройки", ephemeral=True)
                return

            embed = disnake.Embed(
                title="Настройки приветствия",
                color=COLOR_BLUE
            )

            embed.add_field(name="Заголовок", value=config.get("title", "Не задан"), inline=False)
            
            description = config.get("description", "Не задано")
            if len(description) > 300:
                description = description[:300] + "..."
            embed.add_field(name="Описание", value=description, inline=False)
            
            embed.add_field(name="Включено", value="Да" if config.get("is_enabled") else "Нет", inline=True)

            if config.get("color"):
                embed.add_field(name="Цвет", value=f"#{config['color']:06X}", inline=True)

            rules_channel_id = config.get("rules_channel_id")
            if rules_channel_id:
                channel = ctx.guild.get_channel(rules_channel_id)
                embed.add_field(name="Канал правил", value=channel.mention if channel else "Удалён", inline=True)
            else:
                embed.add_field(name="Канал правил", value="Не настроен", inline=True)

            roles_channel_id = config.get("roles_channel_id")
            if roles_channel_id:
                channel = ctx.guild.get_channel(roles_channel_id)
                embed.add_field(name="Канал ролей", value=channel.mention if channel else "Удалён", inline=True)
            else:
                embed.add_field(name="Канал ролей", value="Не настроен", inline=True)

            if config.get("footer_text"):
                embed.add_field(name="Колонтитул", value=config["footer_text"], inline=False)

            if config.get("thumbnail_url"):
                embed.set_thumbnail(url=config["thumbnail_url"])

            embed.set_footer(text="Используйте /welcome setup, /welcome media, /welcome channels для изменения")
            await ctx.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error showing welcome config for guild {ctx.guild.id}: {e}", exc_info=True)
            await ctx.response.send_message(
                "Произошла ошибка при отображении настроек",
                ephemeral=True
            )


def setup(bot: commands.Bot):
    pass
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import disnake
from disnake.ext import commands

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class GeneralCog(commands.Cog):
    _COMMANDS: tuple[dict[str, object], ...] = (
        {"section": "Основное", "command": "/help", "description": "Показать доступные команды"},
        {"section": "Основное", "command": "/ping", "description": "Проверить задержку бота"},
        {"section": "Статистика", "command": "/stats server", "description": "Статистика сервера за 7 или 30 дней"},
        {"section": "Статистика", "command": "/stats user", "description": "Статистика участника"},
        {"section": "Статистика", "command": "/stats channels", "description": "Активные каналы за неделю"},
        {"section": "Статистика", "command": "/stats activity", "description": "Активность по часам"},
        {"section": "Статистика", "command": "/leaderboard", "description": "Топ активных участников"},
        {"section": "Голосовые комнаты", "command": "/send", "description": "Опустить панель управления voice-комнатой"},
        {"section": "Голосовые комнаты", "command": "/voice set_trigger", "description": "Назначить trigger-канал", "permission": "administrator"},
        {"section": "Голосовые комнаты", "command": "/voice remove_trigger", "description": "Удалить trigger-канал", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/sync_roles", "description": "Синхронизировать роли Discord", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/set_auto_role", "description": "Настроить авто-роль новичкам", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/list_roles", "description": "Показать роли сервера", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/set_role_public", "description": "Изменить публичность роли", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/create_panel", "description": "Создать панель ролей", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/panel_add", "description": "Добавить роль в панель", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/panel_remove", "description": "Удалить роль из панели", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/panel_list", "description": "Показать панели ролей", "permission": "administrator"},
        {"section": "Роли и панели", "command": "/delete_panel", "description": "Удалить панель ролей", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/set_channel", "description": "Назначить системный канал", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/list_channels", "description": "Показать системные каналы", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome setup", "description": "Настроить welcome-сообщение", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome media", "description": "Настроить медиа welcome-сообщения", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome channels", "description": "Выбрать каналы для плейсхолдеров", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome toggle", "description": "Включить или выключить welcome", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome preview", "description": "Предпросмотр welcome", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome reset", "description": "Сбросить welcome-настройки", "permission": "administrator"},
        {"section": "Каналы и welcome", "command": "/welcome show", "description": "Показать welcome-настройки", "permission": "administrator"},
        {"section": "Модерация", "command": "/moderation", "description": "Краткая памятка по модерации"},
        {"section": "Модерация", "command": "/warn", "description": "Выдать предупреждение", "permission": "moderate_members"},
        {"section": "Модерация", "command": "/mute", "description": "Выдать таймаут", "permission": "ban_members"},
        {"section": "Модерация", "command": "/unmute", "description": "Снять таймаут", "permission": "moderate_members"},
        {"section": "Модерация", "command": "/kick", "description": "Кикнуть участника", "permission": "kick_members"},
        {"section": "Модерация", "command": "/ban", "description": "Забанить участника", "permission": "ban_members"},
        {"section": "Модерация", "command": "/unban", "description": "Разбанить по ID", "permission": "ban_members"},
        {"section": "Модерация", "command": "/history", "description": "История наказаний участника", "permission": "moderate_members"},
        {"section": "Модерация", "command": "/punishments", "description": "Активные наказания", "permission": "moderate_members"},
        {"section": "Модерация", "command": "/slowmode", "description": "Настроить slowmode канала", "permission": "manage_channels"},
        {"section": "Модерация", "command": "/purge", "description": "Массово удалить сообщения", "permission": "manage_messages"},
        {"section": "Модерация", "command": "/activity_role", "description": "Назначить Activity-роль", "permission": "administrator"},
    )

    def __init__(self, bot: commands.Bot):
        self._bot = bot
        logger.info("GeneralCog initialized")

    @commands.slash_command(name="ping", description="Проверить задержку OmniBot")
    async def ping(self, ctx: disnake.ApplicationCommandInteraction) -> None:
        latency_ms = round(self._bot.latency * 1000)
        embed = disnake.Embed(
            title="OmniBot online",
            description=f"Gateway latency: **{latency_ms} ms**",
            color=disnake.Color.green(),
        )
        embed.set_footer(text="Проверка видна только вам")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        logger.info("Ping command used: guild_id=%s user_id=%s latency_ms=%s", getattr(ctx.guild, "id", None), ctx.author.id, latency_ms)

    @commands.slash_command(name="help", description="Показать доступные команды OmniBot")
    async def help(self, ctx: disnake.ApplicationCommandInteraction) -> None:
        commands_by_section = self.get_available_commands_by_section(ctx.author)
        embed = self._build_help_embed(ctx, commands_by_section)
        await ctx.response.send_message(embed=embed, ephemeral=True)
        logger.info(
            "Help command used: guild_id=%s user_id=%s command_count=%s",
            getattr(ctx.guild, "id", None),
            ctx.author.id,
            sum(len(commands) for commands in commands_by_section.values()),
        )

    def get_available_commands_by_section(self, member: disnake.Member) -> dict[str, list[dict[str, object]]]:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for command in self._COMMANDS:
            if self._is_command_available(member, command):
                grouped[str(command["section"])].append(command)
        return dict(grouped)

    def _is_command_available(self, member: disnake.Member, command: dict[str, object]) -> bool:
        permission = command.get("permission")
        if not permission:
            return True

        guild_permissions = getattr(member, "guild_permissions", None)
        if guild_permissions is None:
            return False

        if getattr(guild_permissions, "administrator", False):
            return True

        return bool(getattr(guild_permissions, str(permission), False))

    def _build_help_embed(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        commands_by_section: dict[str, list[dict[str, object]]],
    ) -> disnake.Embed:
        guild_name = ctx.guild.name if ctx.guild else "Discord"
        embed = disnake.Embed(
            title="OmniBot command center",
            description=(
                f"Доступные команды для **{ctx.author.display_name}** на сервере **{guild_name}**.\n"
                "Показаны только команды, которые подходят вашим текущим правам."
            ),
            color=disnake.Color.blurple(),
        )

        for section, commands_in_section in commands_by_section.items():
            embed.add_field(
                name=section,
                value=self._format_commands(commands_in_section),
                inline=False,
            )

        embed.set_footer(text=f"Всего доступно команд: {sum(len(items) for items in commands_by_section.values())}")
        return embed

    def _format_commands(self, commands_in_section: Iterable[dict[str, object]]) -> str:
        lines = [
            f"`{command['command']}` - {command['description']}"
            for command in commands_in_section
        ]
        return "\n".join(lines)[:1024]

from __future__ import annotations

from typing import Any

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class GlobalApplicationCommandSyncService:
    async def sync(self, bot: Any) -> list[Any]:
        global_commands = await self.sync_global_commands(bot)
        await self.remove_legacy_guild_commands(bot, global_commands)
        return global_commands

    async def sync_global_commands(self, bot: Any) -> list[Any]:
        if bot.application_id is None:
            logger.warning("Global application command sync skipped: application_id is not ready")
            return []

        global_commands = self._collect_global_commands(bot)
        command_names = sorted(command.name for command in global_commands)
        logger.info(
            "Starting manual global application command sync count=%s names=%s",
            len(global_commands),
            ",".join(command_names),
        )

        await bot.bulk_overwrite_global_commands(global_commands)

        logger.info("Global application command sync completed count=%s", len(global_commands))
        return global_commands

    def _collect_global_commands(self, bot: Any) -> list[Any]:
        commands = []
        for command in bot.application_commands_iterator():
            commands.append(command.body)
        return commands

    async def remove_legacy_guild_commands(
        self,
        bot: Any,
        global_commands: list[Any] | None = None,
    ) -> None:
        if global_commands is None:
            global_commands = self._collect_global_commands(bot)

        global_keys = {(command.name, command.type) for command in global_commands}
        if not global_keys:
            logger.info("Legacy guild command cleanup skipped: no global commands collected")
            return

        logger.info("Starting legacy guild command cleanup guild_count=%s", len(bot.guilds))
        for guild in bot.guilds:
            try:
                await self._remove_legacy_guild_commands_for_guild(bot, guild, global_keys)
            except Exception:
                logger.exception("Failed to clean legacy guild commands for guild id=%s", guild.id)

    async def _remove_legacy_guild_commands_for_guild(
        self,
        bot: Any,
        guild: Any,
        global_keys: set[tuple[str, Any]],
    ) -> None:
        guild_commands = await bot.fetch_guild_commands(guild.id, with_localizations=True)
        for command in guild_commands:
            if (command.name, command.type) not in global_keys:
                continue

            await bot.delete_guild_command(guild.id, command.id)
            logger.info(
                "Removed legacy guild command name=%s type=%s guild_id=%s",
                command.name,
                command.type,
                guild.id,
            )

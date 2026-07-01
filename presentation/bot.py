import asyncio
import random
from dataclasses import dataclass

import disnake
from disnake.ext import commands, tasks
from disnake.ext.commands.flags import CommandSyncFlags

from application.services.global_application_command_sync_service import GlobalApplicationCommandSyncService
from infrastructure.config import BotConfig
from infrastructure.logging import get_logger
from infrastructure.network import install_aiohttp_discord_proxy

logger = get_logger(__name__)


@dataclass(frozen=True)
class PresenceItem:
    activity_type: str
    name: str
    status: disnake.Status


class DiscordBot(commands.Bot):
    def __init__(
        self,
        config: BotConfig,
        role_service=None,
        stats_service=None,
    ):
        install_aiohttp_discord_proxy()
        self._config = config
        self._role_service = role_service
        self._stats_service = stats_service
        self._presence_items = self._load_presence_items()
        self._presence_index = random.randrange(len(self._presence_items))
        self._global_command_sync_service = GlobalApplicationCommandSyncService()
        self._global_commands_synced = False

        intents = disnake.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        initial_presence = self._presence_items[self._presence_index]

        super().__init__(
            command_prefix=self._config.command_prefix,
            intents=intents,
            activity=self._build_activity(initial_presence),
            status=initial_presence.status,
            command_sync_flags=self._build_command_sync_flags(),
            proxy=self._config.discord_proxy_url,
        )

        self._ready = asyncio.Event()

        if self._role_service:
            self._role_service.set_bot(self)  

    def _build_command_sync_flags(self) -> CommandSyncFlags:
        flags = CommandSyncFlags.default()
        flags.sync_global_commands = False
        flags.sync_guild_commands = False
        return flags

    async def on_ready(self):
        if not self._ready.is_set():
            self._ready.set()
            
            logger.info("=" * 50)
            logger.info(f"Bot: {self.user.name}")
            logger.info(f"ID: {self.user.id}")
            
            logger.info("Guilds connected: %s", len(self.guilds))
            for guild in self.guilds:
                logger.info("Guild: %s id=%s members=%s", guild.name, guild.id, guild.member_count)
            
            logger.info("=" * 50)
            await self._start_presence_rotation()

            await self._ensure_global_commands_synced()
            await self._global_command_sync_service.remove_legacy_guild_commands(self)
            
            # Синхронизируем роли при старте
            if self.guilds and self._role_service:
                for guild in self.guilds:
                    try:
                        await self._role_service.sync_roles(guild)
                    except Exception as e:
                        logger.error("Failed to sync roles for guild id=%s: %s", guild.id, e)
    async def on_connect(self):
        logger.info("Connected to Discord gateway")
        await self._start_presence_rotation()

    async def _ensure_global_commands_synced(self) -> None:
        if self._global_commands_synced:
            return

        try:
            commands = await self._global_command_sync_service.sync_global_commands(self)
        except Exception:
            logger.exception("Manual global application command sync failed")
            return

        if commands:
            self._global_commands_synced = True
            await self._global_command_sync_service.remove_legacy_guild_commands(self, commands)

    async def on_application_command_error(self, interaction: disnake.Interaction, error: Exception):
        logger.error("Application command error command=%s error=%s", getattr(interaction, "command", None), error, exc_info=True)
        if interaction.response.is_done():
            return
        embed = disnake.Embed(
            title="Ошибка команды",
            description=str(error),
            color=disnake.Color.red(),
        )
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            logger.exception("Failed to send application command error response")

    async def on_interaction_error(self, interaction: disnake.Interaction, error: Exception):
        logger.error("Interaction error custom_id=%s error=%s", getattr(interaction, "custom_id", None), error, exc_info=True)
        if interaction.response.is_done():
            return
        try:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    title="Ошибка взаимодействия",
                    description=str(error),
                    color=disnake.Color.red(),
                ),
                ephemeral=True,
            )
        except Exception:
            logger.exception("Failed to send interaction error response")

    async def close(self):
        """Закрытие бота"""
        logger.info("Closing bot...")
        if self._presence_rotator.is_running():
            self._presence_rotator.cancel()
        await super().close()

    async def _start_presence_rotation(self):
        if not self._config.activity_rotation_enabled or len(self._presence_items) < 2:
            await self._apply_presence(self._presence_items[self._presence_index])
            return

        self._presence_rotator.change_interval(
            seconds=self._config.activity_rotation_interval_seconds
        )

        if not self._presence_rotator.is_running():
            try:
                await self._apply_presence(self._presence_items[self._presence_index])
            except Exception:
                logger.exception("Initial presence update failed")
            self._presence_rotator.start()
            logger.info(
                "Presence rotation started: %s items, %s seconds interval",
                len(self._presence_items),
                self._config.activity_rotation_interval_seconds,
            )

    @tasks.loop(seconds=60)
    async def _presence_rotator(self):
        next_index = (self._presence_index + 1) % len(self._presence_items)
        try:
            await self._apply_presence(self._presence_items[next_index])
        except Exception:
            logger.exception("Presence rotation failed index=%s", next_index)
            return

        self._presence_index = next_index

    @_presence_rotator.before_loop
    async def _before_presence_rotator(self):
        await asyncio.sleep(self._config.activity_rotation_interval_seconds)

    async def _apply_presence(self, item: PresenceItem):
        await self.change_presence(
            activity=self._build_activity(item),
            status=item.status,
        )
        logger.info(
            "Presence updated type=%s status=%s name=%s",
            item.activity_type,
            item.status,
            self._format_presence_text(item.name),
        )

    def _load_presence_items(self) -> list[PresenceItem]:
        configured_items = self._parse_presence_activities(
            self._config.presence_activities
        )
        if configured_items:
            return configured_items

        default_status = self._parse_status(self._config.bot_status)
        activity_name = self._config.activity_name.strip() or "Omnibot | центр управления"

        return [
            PresenceItem("playing", activity_name, default_status),
            PresenceItem("watching", "щит OmniBot над {members} участниками", disnake.Status.online),
            PresenceItem("listening", "/help | роли, логи, войсы", disnake.Status.idle),
            PresenceItem("competing", "с хаосом в логах и побеждаю", disnake.Status.dnd),
            PresenceItem("watching", "пульс сервера: роли, входы, события", disnake.Status.online),
            PresenceItem("playing", "Omnibot OS | порядок без шума", disnake.Status.online),
            PresenceItem("listening", "модераторов и тревожные сигналы", disnake.Status.idle),
            PresenceItem("competing", "за чистый чат и спокойный сервер", disnake.Status.dnd),
            PresenceItem("watching", "dynamic voice rooms как диспетчер", disnake.Status.online),
            PresenceItem("playing", "панель управления без паники", disnake.Status.online),
        ]

    def _parse_presence_activities(self, raw_activities: str) -> list[PresenceItem]:
        if not raw_activities.strip():
            return []

        items = []
        default_status = self._parse_status(self._config.bot_status)

        for raw_item in raw_activities.replace("\n", ";").split(";"):
            raw_item = raw_item.strip()
            if not raw_item:
                continue

            status = default_status
            activity_type = "playing"
            name = raw_item
            parts = [part.strip() for part in raw_item.split(":", 2)]

            if len(parts) == 3 and self._is_status(parts[0]):
                status = self._parse_status(parts[0])
                activity_type = parts[1]
                name = parts[2]
            elif len(parts) >= 2:
                activity_type = parts[0]
                name = parts[1]

            if not name:
                continue

            items.append(
                PresenceItem(
                    self._normalize_activity_type(activity_type),
                    name,
                    status,
                )
            )

        return items

    def _build_activity(self, item: PresenceItem):
        name = self._format_presence_text(item.name)

        if item.activity_type == "watching":
            return disnake.Activity(type=disnake.ActivityType.watching, name=name)
        if item.activity_type == "listening":
            return disnake.Activity(type=disnake.ActivityType.listening, name=name)
        if item.activity_type == "competing":
            return disnake.Activity(type=disnake.ActivityType.competing, name=name)

        return disnake.Game(name=name)

    def _format_presence_text(self, text: str) -> str:
        try:
            guilds = self.guilds
        except AttributeError:
            guilds = []

        member_count = sum(guild.member_count or 0 for guild in guilds)
        if member_count == 0:
            member_count = sum(len(guild.members) for guild in guilds)

        values = {
            "guilds": len(guilds),
            "members": member_count,
            "prefix": self._config.command_prefix,
        }

        try:
            formatted = text.format(**values)
        except (KeyError, ValueError):
            formatted = text

        return formatted[:128]

    def _normalize_activity_type(self, activity_type: str) -> str:
        activity_type = activity_type.strip().lower()
        aliases = {
            "game": "playing",
            "play": "playing",
            "playing": "playing",
            "watch": "watching",
            "watching": "watching",
            "listen": "listening",
            "listening": "listening",
            "compete": "competing",
            "competing": "competing",
        }
        return aliases.get(activity_type, "playing")

    def _parse_status(self, status: str) -> disnake.Status:
        statuses = {
            "online": disnake.Status.online,
            "idle": disnake.Status.idle,
            "dnd": disnake.Status.dnd,
            "do_not_disturb": disnake.Status.dnd,
            "invisible": disnake.Status.invisible,
            "offline": disnake.Status.invisible,
        }
        return statuses.get(status.strip().lower(), disnake.Status.online)

    def _is_status(self, value: str) -> bool:
        return value.strip().lower() in {
            "online",
            "idle",
            "dnd",
            "do_not_disturb",
            "invisible",
            "offline",
        }

from typing import Any

from activity.server.services.access_service import ActivityAccessService
from activity.server.services.discord_service import DiscordService
from activity.server.dependencies import get_db, get_role_purpose_service
from infrastructure.config import get_config
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class BotSettingsService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._discord_service = DiscordService()

    async def get_settings(self, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Loading Activity bot settings guild_id=%s", guild_id)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "bot-settings")
        config = get_config()
        channel_rows = await get_db().fetch_all(
            "SELECT purpose, channel_id FROM server_channel_purposes WHERE guild_id = ?",
            (guild_id,),
        )
        return {
            "guild_id": str(guild_id),
            "command_prefix": config.command_prefix,
            "activity_name": "",
            "bot_status": "",
            "activity_rotation_enabled": config.activity_rotation_enabled,
            "activity_rotation_interval_seconds": config.activity_rotation_interval_seconds,
            "log_level": config.log_level,
            "retention": {
                "message_log_retention_days": config.message_log_retention_days,
                "punishment_retention_days": config.punishment_retention_days,
            },
            "channels": await self._discord_service.list_channels(str(guild_id), "text"),
            "roles": await self._discord_service.list_roles(str(guild_id)),
            "channel_purposes": {row["purpose"]: str(row["channel_id"]) for row in channel_rows},
            "activity_roles": {
                purpose: str(role_id)
                for purpose, role_id in (await get_role_purpose_service().get_all_roles(guild_id)).items()
            },
        }

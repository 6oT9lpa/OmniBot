from typing import Any

from activity.server.dependencies import get_db
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.discord_service import DiscordService
from activity.server.schemas.ai_moderation_channels import AiModerationChannelsPayload
from activity.server.schemas.ai_moderation_policy import AiModerationPolicyPayload
from core.domain.default_ai_moderation_policy import default_ai_moderation_policy
from core.domain.ai_moderation_guild_policy import AiModerationGuildPolicy
from infrastructure.logging import get_logger
from psycopg.types.json import Jsonb

logger = get_logger(__name__)


class AiModerationService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._discord_service = DiscordService()

    async def get_settings(self, guild_id: int, access_token: str) -> dict[str, Any]:
        await self._access_service.ensure_module_access(access_token, str(guild_id), "ai-moderator")
        channels = await get_db().fetch_all("SELECT channel_id FROM ai_moderation_channels WHERE guild_id = ? ORDER BY channel_id", (guild_id,))
        policy_row = await get_db().fetch_one("SELECT policy_json FROM ai_moderation_settings WHERE guild_id = ?", (guild_id,))
        log_row = await get_db().fetch_one("SELECT channel_id FROM server_channel_purposes WHERE guild_id = ? AND purpose = ?", (guild_id, "ai_moderation_log"))
        stored_policy = dict(policy_row["policy_json"]) if policy_row and isinstance(policy_row["policy_json"], dict) else None
        effective_policy, is_default_policy = self._effective_policy(stored_policy, guild_id)
        return {
            "guild_id": str(guild_id),
            "channels": [str(row["channel_id"]) for row in channels],
            "log_channel_id": str(log_row["channel_id"]) if log_row else None,
            "policy": effective_policy,
            "is_default_policy": is_default_policy,
            "available_channels": await self._discord_service.list_channels(str(guild_id), "moderation"),
        }

    async def save_channels(self, payload: AiModerationChannelsPayload, access_token: str) -> dict[str, Any]:
        await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "ai-moderator", "manage")
        channel_ids = set(payload.channel_ids)
        await self._discord_service.validate_moderation_channel_ids(str(payload.guild_id), channel_ids)
        await get_db().execute("DELETE FROM ai_moderation_channels WHERE guild_id = ?", (payload.guild_id,))
        for channel_id in channel_ids:
            await get_db().execute("INSERT INTO ai_moderation_channels (guild_id, channel_id) VALUES (?, ?) ON CONFLICT DO NOTHING", (payload.guild_id, channel_id))
        await get_db().commit()
        return await self.get_settings(payload.guild_id, access_token)

    def _effective_policy(self, stored_policy: dict[str, object] | None, guild_id: int) -> tuple[dict[str, object], bool]:
        if stored_policy is None:
            return default_ai_moderation_policy().model_dump(mode="json"), True
        try:
            return AiModerationGuildPolicy.model_validate(stored_policy).model_dump(mode="json"), False
        except ValueError:
            logger.warning("Invalid stored AI moderation policy ignored guild_id=%s", guild_id)
            return default_ai_moderation_policy().model_dump(mode="json"), True

    async def save_policy(self, payload: AiModerationPolicyPayload, access_token: str) -> dict[str, Any]:
        await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "ai-moderator", "manage")
        await get_db().execute(
            "INSERT INTO ai_moderation_settings (guild_id, policy_json) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET policy_json = excluded.policy_json, updated_at = CURRENT_TIMESTAMP",
            (payload.guild_id, Jsonb(payload.policy.model_dump(mode="json"))),
        )
        await get_db().commit()
        return await self.get_settings(payload.guild_id, access_token)

from typing import Optional

from disnake.ext import commands

from application.services.ai_moderation_queue import AiModerationQueue
from application.services.ai_moderation_settings_service import AiModerationSettingsService
from infrastructure.ai.ai_moderator_api_client import AiModeratorApiClient
from infrastructure.logging import get_logger
from presentation.cogs.ai_moderation_cog import AiModerationCog

logger = get_logger(__name__)


class AiModerationModule:
    def __init__(self, container) -> None:
        self._container = container
        self._cog: Optional[AiModerationCog] = None

    async def get_cog(self, bot: commands.Bot) -> Optional[AiModerationCog]:
        if self._cog is not None:
            return self._cog
        api_key = self._container.config.ai_moderator_internal_api_key
        if api_key is None:
            logger.warning("AI moderation cog is disabled because AI_MODERATOR_INTERNAL_API_KEY is missing")
            return None
        settings_service = await self._container.get_ai_moderation_settings_service()
        channel_service = await self._container.get_channel_service()
        client = AiModeratorApiClient(
            self._container.config.ai_moderator_api_url,
            api_key.get_secret_value(),
            self._container.config.ai_moderator_request_timeout_seconds,
        )
        queue = AiModerationQueue(client, self._container.config.ai_moderator_worker_count, self._container.config.ai_moderator_queue_size, self._handle_decision)
        self._cog = AiModerationCog(bot, settings_service, channel_service, queue)
        return self._cog

    async def _handle_decision(self, request, decision) -> None:
        if self._cog is not None:
            await self._cog.handle_decision(request, decision)

    async def shutdown(self) -> None:
        if self._cog is not None:
            await self._cog.shutdown()
            self._cog = None

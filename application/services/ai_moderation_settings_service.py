from typing import Mapping

from core.interfaces.repositories.ai_moderation_repository_interface import AiModerationRepositoryInterface


class AiModerationSettingsService:
    def __init__(self, repository: AiModerationRepositoryInterface) -> None:
        self._repository = repository

    async def add_channel(self, guild_id: int, channel_id: int) -> None:
        await self._repository.add_channel(guild_id, channel_id)

    async def remove_channel(self, guild_id: int, channel_id: int) -> bool:
        return await self._repository.remove_channel(guild_id, channel_id)

    async def list_channels(self, guild_id: int) -> list[int]:
        return await self._repository.list_channels(guild_id)

    async def get_policy(self, guild_id: int) -> dict[str, object]:
        return await self._repository.get_policy(guild_id)

    async def save_policy(self, guild_id: int, policy: Mapping[str, object]) -> None:
        await self._repository.save_policy(guild_id, policy)

    async def is_enabled_for_channel(self, guild_id: int, channel_id: int) -> bool:
        return channel_id in await self._repository.list_channels(guild_id)

    async def record_event(self, guild_id: int, channel_id: int, message_id: int, user_id: int, risk_score: float, action: str, primary_label: str, labels: tuple[str, ...], status: str) -> None:
        await self._repository.save_event(guild_id, channel_id, message_id, user_id, risk_score, action, primary_label, labels, status)

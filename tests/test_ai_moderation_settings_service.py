import pytest

from application.services.ai_moderation_settings_service import AiModerationSettingsService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class _RepositoryStub:
    def __init__(self) -> None:
        self.channels: set[int] = set()
        self.policy: dict[str, object] = {}

    async def add_channel(self, _: int, channel_id: int) -> None: self.channels.add(channel_id)
    async def remove_channel(self, _: int, channel_id: int) -> bool:
        if channel_id not in self.channels: return False
        self.channels.remove(channel_id); return True
    async def list_channels(self, _: int) -> list[int]: return sorted(self.channels)
    async def get_policy(self, _: int) -> dict[str, object]: return dict(self.policy)
    async def save_policy(self, _: int, policy: dict[str, object]) -> None: self.policy = dict(policy)
    async def save_event(self, *args) -> None: return None


@pytest.mark.asyncio
async def test_settings_service_persists_channels_and_policy() -> None:
    logger.info("AI settings test expected=stored channel and policy actual=service workflow")
    service = AiModerationSettingsService(_RepositoryStub())
    await service.add_channel(1, 10)
    await service.save_policy(1, {"blacklist_words": ["blocked"]})
    assert await service.is_enabled_for_channel(1, 10)
    assert (await service.get_policy(1))["blacklist_words"] == ["blocked"]

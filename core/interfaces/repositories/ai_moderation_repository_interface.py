from abc import ABC, abstractmethod
from typing import Mapping


class AiModerationRepositoryInterface(ABC):
    @abstractmethod
    async def add_channel(self, guild_id: int, channel_id: int) -> None: ...

    @abstractmethod
    async def remove_channel(self, guild_id: int, channel_id: int) -> bool: ...

    @abstractmethod
    async def list_channels(self, guild_id: int) -> list[int]: ...

    @abstractmethod
    async def get_policy(self, guild_id: int) -> dict[str, object]: ...

    @abstractmethod
    async def save_policy(self, guild_id: int, policy: Mapping[str, object]) -> None: ...

    @abstractmethod
    async def save_event(self, guild_id: int, channel_id: int, message_id: int, user_id: int, risk_score: float, action: str, primary_label: str, labels: tuple[str, ...], status: str) -> None: ...

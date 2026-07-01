from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from application.dto.creator_alert_dto import CreatorAlertSubscriptionInput
from core.domain.creator_alert import CreatorAlertSubscription


class CreatorAlertRepositoryInterface(ABC):
    @abstractmethod
    async def list_by_guild(self, guild_id: int) -> list[CreatorAlertSubscription]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(self, guild_id: int, user_id: int) -> list[CreatorAlertSubscription]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, subscription_id: int) -> Optional[CreatorAlertSubscription]:
        raise NotImplementedError

    @abstractmethod
    async def count_by_user(self, guild_id: int, user_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def save(self, payload: CreatorAlertSubscriptionInput) -> CreatorAlertSubscription:
        raise NotImplementedError

    @abstractmethod
    async def delete_for_user(self, guild_id: int, user_id: int, subscription_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def mark_event(self, subscription_id: int, event_id: str) -> None:
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from application.dto.creator_alert_dto import CreatorAlertSubscriptionInput
from core.domain.creator_alert import CreatorAlertSubscription


class CreatorAlertServiceInterface(ABC):
    @abstractmethod
    async def list_sources(
        self,
        guild_id: int,
        user_id: Optional[int] = None,
    ) -> list[CreatorAlertSubscription]:
        raise NotImplementedError

    @abstractmethod
    async def save_source(self, payload: CreatorAlertSubscriptionInput) -> CreatorAlertSubscription:
        raise NotImplementedError

    @abstractmethod
    async def remove_source(self, guild_id: int, user_id: int, subscription_id: int) -> bool:
        raise NotImplementedError

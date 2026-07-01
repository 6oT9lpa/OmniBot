from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.domain.creator_alert import CreatorContentEvent


class CreatorPlatformClientInterface(ABC):
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_latest_event(
        self,
        channel_url: str,
        external_channel_id: Optional[str] = None,
    ) -> Optional[CreatorContentEvent]:
        raise NotImplementedError

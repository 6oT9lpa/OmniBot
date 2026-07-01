from __future__ import annotations

from typing import Optional

from core.domain.creator_alert import CreatorContentEvent
from core.interfaces.clients import CreatorPlatformClientInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class KickClient(CreatorPlatformClientInterface):
    @property
    def is_configured(self) -> bool:
        return False

    async def fetch_latest_event(
        self,
        channel_url: str,
        external_channel_id: Optional[str] = None,
    ) -> Optional[CreatorContentEvent]:
        logger.info(
            "Kick API check skipped url=%s external_channel_id=%s",
            channel_url,
            external_channel_id,
        )
        return None

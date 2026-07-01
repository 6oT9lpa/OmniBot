from __future__ import annotations

from typing import Optional

from application.dto.creator_alert_dto import CreatorAlertSubscriptionInput
from core.domain.creator_alert import (
    CreatorAlertSubscription,
    CreatorContentEvent,
    CreatorPlatform,
)
from core.domain.server_role_purpose import ServerRolePurpose
from core.interfaces.clients import CreatorPlatformClientInterface
from core.interfaces.repositories import (
    ChannelConfigRepositoryInterface,
    CreatorAlertRepositoryInterface,
)
from core.interfaces.services import (
    CreatorAlertServiceInterface,
    ServerRolePurposeServiceInterface,
)
from core.domain.channel_purpose import ChannelPurpose
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class CreatorAlertService(CreatorAlertServiceInterface):
    MAX_SOURCES_PER_USER = 5

    def __init__(
        self,
        repository: CreatorAlertRepositoryInterface,
        channel_repository: ChannelConfigRepositoryInterface,
        role_purpose_service: ServerRolePurposeServiceInterface,
        platform_clients: dict[CreatorPlatform, CreatorPlatformClientInterface],
    ):
        self._repository = repository
        self._channel_repository = channel_repository
        self._role_purpose_service = role_purpose_service
        self._platform_clients = platform_clients

    async def list_sources(
        self,
        guild_id: int,
        user_id: Optional[int] = None,
    ) -> list[CreatorAlertSubscription]:
        if user_id is not None:
            return await self._repository.list_by_user(guild_id, user_id)
        return await self._repository.list_by_guild(guild_id)

    async def save_source(self, payload: CreatorAlertSubscriptionInput) -> CreatorAlertSubscription:
        count = await self._repository.count_by_user(payload.guild_id, payload.user_id)
        existing = await self._repository.list_by_user(payload.guild_id, payload.user_id)
        is_update = any(
            source.platform == payload.platform
            and source.channel_url == payload.channel_url
            and source.alert_kind == payload.alert_kind
            for source in existing
        )
        if count >= self.MAX_SOURCES_PER_USER and not is_update:
            logger.warning(
                "Creator alert source limit reached guild_id=%s user_id=%s",
                payload.guild_id,
                payload.user_id,
            )
            raise ValueError("Creator alert source limit is 5 per user")

        saved = await self._repository.save(payload)
        logger.info("Creator alert source saved subscription_id=%s", saved.id)
        return saved

    async def remove_source(self, guild_id: int, user_id: int, subscription_id: int) -> bool:
        removed = await self._repository.delete_for_user(guild_id, user_id, subscription_id)
        logger.info(
            "Creator alert source remove result guild_id=%s user_id=%s subscription_id=%s removed=%s",
            guild_id,
            user_id,
            subscription_id,
            removed,
        )
        return removed

    async def get_source_for_user(
        self,
        guild_id: int,
        user_id: int,
        subscription_id: int,
    ) -> Optional[CreatorAlertSubscription]:
        source = await self._repository.get_by_id(subscription_id)
        if not source or source.guild_id != guild_id or source.user_id != user_id:
            logger.warning(
                "Creator alert source lookup denied guild_id=%s user_id=%s subscription_id=%s",
                guild_id,
                user_id,
                subscription_id,
            )
            return None
        return source

    async def check_subscription(
        self,
        subscription: CreatorAlertSubscription,
    ) -> Optional[CreatorContentEvent]:
        if not subscription.active:
            logger.info("Skipping inactive creator alert subscription_id=%s", subscription.id)
            return None
        client = self._platform_clients.get(subscription.platform)
        if not client:
            logger.warning("No creator platform client platform=%s", subscription.platform.value)
            return None
        if not getattr(client, "is_configured", True):
            logger.warning(
                "Creator platform client is not configured platform=%s subscription_id=%s",
                subscription.platform.value,
                subscription.id,
            )
            return None

        event = await client.fetch_latest_event(
            subscription.channel_url,
            subscription.external_channel_id,
        )
        if not event:
            return None
        if event.event_id == subscription.last_event_id:
            logger.info(
                "Creator alert event already announced subscription_id=%s event_id=%s",
                subscription.id,
                event.event_id,
            )
            return None
        return event

    async def mark_announced(self, subscription_id: int, event_id: str) -> None:
        await self._repository.mark_event(subscription_id, event_id)

    async def get_announce_channel_id(self, guild_id: int) -> Optional[int]:
        return await self._channel_repository.get_purpose_channel(guild_id, ChannelPurpose.STREAM_ANNOUNCE)

    async def get_default_ping_role_id(self, guild_id: int) -> Optional[int]:
        return await self._role_purpose_service.get_role(guild_id, ServerRolePurpose.PING_STREAM)

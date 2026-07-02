from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from application.dto.creator_alert_dto import CreatorAlertSubscriptionInput
from core.domain.creator_alert import (
    CreatorAlertKind,
    CreatorAlertSubscription,
    CreatorPlatform,
)
from core.interfaces.repositories.creator_alert_repository_interface import (
    CreatorAlertRepositoryInterface,
)
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class CreatorAlertRepository(CreatorAlertRepositoryInterface, BaseRepository):
    _TABLE_NAME = "creator_alert_subscriptions"

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def list_by_guild(self, guild_id: int) -> list[CreatorAlertSubscription]:
        logger.info("Listing creator alert subscriptions guild_id=%s", guild_id)
        rows = await self.fetch_all(
            """
            SELECT * FROM creator_alert_subscriptions
            WHERE guild_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (guild_id,),
        )
        return [self._to_entity(row) for row in rows]

    async def list_by_user(self, guild_id: int, user_id: int) -> list[CreatorAlertSubscription]:
        logger.info(
            "Listing creator alert subscriptions guild_id=%s user_id=%s",
            guild_id,
            user_id,
        )
        rows = await self.fetch_all(
            """
            SELECT * FROM creator_alert_subscriptions
            WHERE guild_id = ? AND user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (guild_id, user_id),
        )
        return [self._to_entity(row) for row in rows]

    async def get_by_id(self, subscription_id: int) -> Optional[CreatorAlertSubscription]:
        row = await self.fetch_one(
            "SELECT * FROM creator_alert_subscriptions WHERE id = ?",
            (subscription_id,),
        )
        return self._to_entity(row) if row else None

    async def count_by_user(self, guild_id: int, user_id: int) -> int:
        row = await self.fetch_one(
            """
            SELECT COUNT(*) AS total FROM creator_alert_subscriptions
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id),
        )
        return int(row["total"]) if row else 0

    async def save(self, payload: CreatorAlertSubscriptionInput) -> CreatorAlertSubscription:
        logger.info(
            "Saving creator alert subscription guild_id=%s user_id=%s platform=%s url=%s",
            payload.guild_id,
            payload.user_id,
            payload.platform.value,
            payload.channel_url,
        )
        title_template = payload.title_template or "{creator.name} is live on {platform}"
        description_template = (
            payload.description_template
            or "{creator.ping} {creator.name} started streaming {game}\n{url}"
        )
        await self.execute(
            """
            INSERT INTO creator_alert_subscriptions (
                guild_id, user_id, platform, channel_url, channel_name,
                external_channel_id, alert_kind, title_template,
                description_template, button_label, color, ping_role_id, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, platform, channel_url, alert_kind)
            DO UPDATE SET
                channel_name = excluded.channel_name,
                external_channel_id = excluded.external_channel_id,
                title_template = excluded.title_template,
                description_template = excluded.description_template,
                button_label = excluded.button_label,
                color = excluded.color,
                ping_role_id = excluded.ping_role_id,
                active = excluded.active,
                last_event_id = CASE
                    WHEN COALESCE(creator_alert_subscriptions.external_channel_id, '') != COALESCE(excluded.external_channel_id, '')
                    THEN NULL
                    ELSE creator_alert_subscriptions.last_event_id
                END,
                last_checked_at = CASE
                    WHEN COALESCE(creator_alert_subscriptions.external_channel_id, '') != COALESCE(excluded.external_channel_id, '')
                    THEN NULL
                    ELSE creator_alert_subscriptions.last_checked_at
                END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                payload.guild_id,
                payload.user_id,
                payload.platform.value,
                payload.channel_url,
                payload.channel_name,
                payload.external_channel_id,
                payload.alert_kind.value,
                title_template,
                description_template,
                payload.button_label,
                payload.color,
                payload.ping_role_id,
                1 if payload.active else 0,
            ),
        )
        await self.commit()
        row = await self.fetch_one(
            """
            SELECT * FROM creator_alert_subscriptions
            WHERE guild_id = ? AND user_id = ? AND platform = ? AND channel_url = ? AND alert_kind = ?
            """,
            (
                payload.guild_id,
                payload.user_id,
                payload.platform.value,
                payload.channel_url,
                payload.alert_kind.value,
            ),
        )
        if not row:
            raise RuntimeError("Failed to reload creator alert subscription after save")
        return self._to_entity(row)

    async def delete_for_user(self, guild_id: int, user_id: int, subscription_id: int) -> bool:
        logger.info(
            "Deleting creator alert subscription guild_id=%s user_id=%s subscription_id=%s",
            guild_id,
            user_id,
            subscription_id,
        )
        cursor = await self.execute(
            """
            DELETE FROM creator_alert_subscriptions
            WHERE guild_id = ? AND user_id = ? AND id = ?
            """,
            (guild_id, user_id, subscription_id),
        )
        await self.commit()
        return bool(cursor.rowcount)

    async def mark_event(self, subscription_id: int, event_id: str) -> None:
        logger.info(
            "Marking creator alert event subscription_id=%s event_id=%s",
            subscription_id,
            event_id,
        )
        await self.execute(
            """
            UPDATE creator_alert_subscriptions
            SET last_event_id = ?, last_checked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (event_id, subscription_id),
        )
        await self.commit()

    def _to_entity(self, row: dict[str, Any]) -> CreatorAlertSubscription:
        return CreatorAlertSubscription(
            id=int(row["id"]) if row.get("id") is not None else None,
            guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]),
            platform=CreatorPlatform(row["platform"]),
            channel_url=row["channel_url"],
            channel_name=row.get("channel_name"),
            external_channel_id=row.get("external_channel_id"),
            alert_kind=CreatorAlertKind(row.get("alert_kind") or CreatorAlertKind.STREAM.value),
            title_template=row.get("title_template") or "{creator.name} is live on {platform}",
            description_template=(
                row.get("description_template")
                or "{creator.ping} {creator.name} started streaming {game}\n{url}"
            ),
            button_label=row.get("button_label") or "Watch",
            color=int(row.get("color") or 0x5865F2),
            ping_role_id=int(row["ping_role_id"]) if row.get("ping_role_id") else None,
            active=bool(row.get("active", 1)),
            last_event_id=row.get("last_event_id"),
            last_checked_at=self._parse_datetime(row.get("last_checked_at")),
            created_at=self._parse_datetime(row.get("created_at")),
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            logger.warning("Failed to parse creator alert datetime value=%s", value)
            return None

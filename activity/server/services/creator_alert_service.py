from typing import Any

from fastapi import HTTPException

from activity.server.dependencies import get_db, get_role_purpose_service
from activity.server.schemas.creator_alerts import CreatorAlertSourcePayload, CreatorAlertTestPayload
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.creator_alert_publish_service import CreatorAlertPublishService
from activity.server.utils.creator_alert_messages import build_creator_alert_message
from core.domain.server_role_purpose import ServerRolePurpose
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class CreatorAlertService:
    MAX_SOURCES_PER_USER = 5

    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._publish_service = CreatorAlertPublishService()

    async def list_sources(self, guild_id: int, access_token: str) -> list[dict[str, Any]]:
        logger.info("Listing creator alert sources guild_id=%s", guild_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(guild_id), "creator-alerts")
        if not (access["is_admin"] or access["is_streamer"]):
            logger.warning("Creator alert list denied guild_id=%s user_id=%s", guild_id, user.get("id"))
            raise HTTPException(status_code=403, detail="Creator or administrator access is required")

        clauses = ["guild_id = ?"]
        params: list[Any] = [guild_id]
        if not access["is_admin"]:
            clauses.append("user_id = ?")
            params.append(int(user["id"]))

        rows = await get_db().fetch_all(
            f"""
            SELECT id, user_id, guild_id, platform, channel_url, channel_name,
                   external_channel_id, alert_kind, title_template, description_template,
                   button_label, color, ping_role_id, active, last_event_id,
                   last_checked_at, created_at
            FROM creator_alert_subscriptions
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            """,
            tuple(params),
        )
        return [self._serialize_source(row) for row in rows]

    async def save_source(self, payload: CreatorAlertSourcePayload, access_token: str) -> dict[str, Any]:
        logger.info("Saving creator alert source guild_id=%s platform=%s", payload.guild_id, payload.platform)
        user, access = await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "creator-alerts", "edit")
        if not (access["is_admin"] or access["is_streamer"]):
            logger.warning("Creator alert save denied guild_id=%s user_id=%s", payload.guild_id, user.get("id"))
            raise HTTPException(status_code=403, detail="Creator or administrator access is required")

        owner_id = payload.user_id if access["is_admin"] and payload.user_id else int(user["id"])
        if not access["is_admin"]:
            payload.ping_role_id = await get_role_purpose_service().get_role(
                payload.guild_id,
                ServerRolePurpose.PING_STREAM,
            )
        elif not payload.ping_role_id:
            payload.ping_role_id = await get_role_purpose_service().get_role(
                payload.guild_id,
                ServerRolePurpose.PING_STREAM,
            )
        source_count = await get_db().fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM creator_alert_subscriptions
            WHERE guild_id = ? AND user_id = ?
            """,
            (payload.guild_id, owner_id),
        )
        existing = await self._find_existing(payload, owner_id)
        if int(source_count["total"]) >= self.MAX_SOURCES_PER_USER and not existing:
            logger.warning("Creator alert source limit reached guild_id=%s user_id=%s", payload.guild_id, owner_id)
            raise HTTPException(status_code=400, detail="Creator Alerts source limit is 5 per user")

        title_template = payload.title_template or "{creator.name} is active on {platform}"
        description_template = (
            payload.description_template
            or payload.template
            or "{creator.ping} {creator.name} started streaming {game}\n{url}"
        )
        values = (
            payload.platform,
            payload.channel_url,
            payload.channel_name,
            payload.external_channel_id,
            payload.alert_kind,
            title_template,
            description_template,
            payload.button_label,
            payload.color,
            payload.ping_role_id,
            int(payload.active),
        )
        if existing:
            should_reset_event = self._identity_changed(existing, payload)
            await get_db().execute(
                """
                UPDATE creator_alert_subscriptions
                SET platform = ?, channel_url = ?, channel_name = ?, external_channel_id = ?, alert_kind = ?,
                    title_template = ?, description_template = ?, button_label = ?, color = ?,
                    ping_role_id = ?, active = ?,
                    last_event_id = CASE WHEN ? THEN NULL ELSE last_event_id END,
                    last_checked_at = CASE WHEN ? THEN NULL ELSE last_checked_at END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (*values, should_reset_event, should_reset_event, existing["id"]),
            )
            source_id = int(existing["id"])
        else:
            await get_db().execute(
                """
                INSERT INTO creator_alert_subscriptions (
                    user_id, guild_id, platform, channel_url, channel_name, external_channel_id,
                    alert_kind, title_template, description_template, button_label, color,
                    ping_role_id, active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_id,
                    payload.guild_id,
                    *values,
                ),
            )
            source_id = await self._resolve_inserted_source_id(payload, owner_id)
        await get_db().commit()
        saved = await get_db().fetch_one(
            "SELECT * FROM creator_alert_subscriptions WHERE id = ?",
            (source_id,),
        )
        if not saved:
            raise HTTPException(status_code=500, detail="Saved source was not found")
        logger.info("Creator alert source saved guild_id=%s source_id=%s", payload.guild_id, source_id)
        serialized = self._serialize_source(saved)
        await self._publish_service.publish_saved_source_if_live(serialized)
        return serialized

    async def delete_source(self, guild_id: int, source_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Deleting creator alert source guild_id=%s source_id=%s", guild_id, source_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(guild_id), "creator-alerts", "edit")
        clauses = ["guild_id = ?", "id = ?"]
        params: list[Any] = [guild_id, source_id]
        if not access["is_admin"]:
            clauses.append("user_id = ?")
            params.append(int(user["id"]))
        cursor = await get_db().execute(
            f"DELETE FROM creator_alert_subscriptions WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
        await get_db().commit()
        if not cursor.rowcount:
            logger.warning(
                "Creator alert source delete missed guild_id=%s source_id=%s user_id=%s",
                guild_id,
                source_id,
                user.get("id"),
            )
            raise HTTPException(status_code=404, detail="Creator source was not found")
        logger.info("Creator alert source deleted guild_id=%s source_id=%s", guild_id, source_id)
        return {
            "deleted": True,
            "id": source_id,
        }

    async def preview_alert(self, payload: CreatorAlertTestPayload, access_token: str) -> dict[str, Any]:
        logger.info("Previewing creator alert guild_id=%s platform=%s", payload.guild_id, payload.platform)
        _, access = await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "creator-alerts", "edit")
        if not (access["is_admin"] or access["is_streamer"]):
            raise HTTPException(status_code=403, detail="Creator or administrator access is required")
        if not access["is_admin"]:
            payload.ping_role_id = await get_role_purpose_service().get_role(
                payload.guild_id,
                ServerRolePurpose.PING_STREAM,
            )
        elif not payload.ping_role_id:
            payload.ping_role_id = await get_role_purpose_service().get_role(
                payload.guild_id,
                ServerRolePurpose.PING_STREAM,
            )
        return build_creator_alert_message(payload)

    async def _find_existing(
        self,
        payload: CreatorAlertSourcePayload,
        owner_id: int,
    ) -> dict[str, Any] | None:
        if payload.id:
            return await get_db().fetch_one(
                """
                SELECT id, platform, channel_url, external_channel_id, alert_kind
                FROM creator_alert_subscriptions
                WHERE guild_id = ? AND user_id = ? AND id = ?
                """,
                (payload.guild_id, owner_id, payload.id),
            )
        return await get_db().fetch_one(
            """
            SELECT id, platform, channel_url, external_channel_id, alert_kind
            FROM creator_alert_subscriptions
            WHERE guild_id = ? AND user_id = ? AND platform = ? AND channel_url = ? AND alert_kind = ?
            LIMIT 1
            """,
            (payload.guild_id, owner_id, payload.platform, payload.channel_url, payload.alert_kind),
        )

    def _identity_changed(self, existing: dict[str, Any], payload: CreatorAlertSourcePayload) -> bool:
        """A changed source identity must be checked as a new stream target by the bot monitor."""
        return any(
            (
                existing.get("platform") != payload.platform,
                existing.get("channel_url") != payload.channel_url,
                (existing.get("external_channel_id") or None) != (payload.external_channel_id or None),
                (existing.get("alert_kind") or "stream") != payload.alert_kind,
            )
        )

    def _serialize_source(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "user_id": str(row["user_id"]),
            "guild_id": str(row["guild_id"]),
            "platform": row["platform"],
            "channel_url": row["channel_url"],
            "channel_name": row.get("channel_name"),
            "external_channel_id": row.get("external_channel_id"),
            "alert_kind": row.get("alert_kind") or "stream",
            "title_template": row.get("title_template"),
            "description_template": row.get("description_template"),
            "button_label": row.get("button_label") or "Watch",
            "color": int(row.get("color") or 0x5865F2),
            "ping_role_id": str(row["ping_role_id"]) if row.get("ping_role_id") else None,
            "active": bool(row.get("active", 1)),
            "last_event_id": row.get("last_event_id"),
            "last_checked_at": row.get("last_checked_at"),
            "created_at": row.get("created_at"),
        }

    async def _resolve_inserted_source_id(
        self,
        payload: CreatorAlertSourcePayload,
        owner_id: int,
    ) -> int:
        row = await self._find_existing(payload, owner_id)
        if not row:
            logger.error(
                "Creator alert source insert could not be reloaded guild_id=%s user_id=%s platform=%s",
                payload.guild_id,
                owner_id,
                payload.platform,
            )
            raise HTTPException(status_code=500, detail="Saved source was not found")
        return int(row["id"])

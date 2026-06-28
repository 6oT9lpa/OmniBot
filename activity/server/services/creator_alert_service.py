from typing import Any

from fastapi import HTTPException

from activity.server.dependencies import get_db
from activity.server.schemas.creator_alerts import CreatorAlertSourcePayload, CreatorAlertTestPayload
from activity.server.services.access_service import ActivityAccessService
from activity.server.utils.creator_alert_messages import build_creator_alert_message
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class CreatorAlertService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()

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

        return await get_db().fetch_all(
            f"""
            SELECT id, user_id, guild_id, platform, channel_url, channel_name, template,
                   ping_role_id, active, last_stream_id, last_check, created_at
            FROM streamers
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
            """,
            tuple(params),
        )

    async def save_source(self, payload: CreatorAlertSourcePayload, access_token: str) -> dict[str, Any]:
        logger.info("Saving creator alert source guild_id=%s platform=%s", payload.guild_id, payload.platform)
        user, access = await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "creator-alerts", "edit")
        if not (access["is_admin"] or access["is_streamer"]):
            logger.warning("Creator alert save denied guild_id=%s user_id=%s", payload.guild_id, user.get("id"))
            raise HTTPException(status_code=403, detail="Creator or administrator access is required")

        owner_id = payload.user_id if access["is_admin"] and payload.user_id else int(user["id"])
        existing = await get_db().fetch_one(
            """
            SELECT id FROM streamers
            WHERE user_id = ? AND platform = ? AND (guild_id = ? OR guild_id = 0)
            ORDER BY CASE WHEN guild_id = ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (owner_id, payload.platform, payload.guild_id, payload.guild_id),
        )
        values = (
            payload.channel_url,
            payload.channel_name,
            payload.template,
            payload.ping_role_id,
            1 if payload.active else 0,
        )
        if existing:
            await get_db().execute(
                """
                UPDATE streamers
                SET channel_url = ?, channel_name = ?, template = ?, ping_role_id = ?, active = ?, guild_id = ?
                WHERE id = ?
                """,
                (*values, payload.guild_id, existing["id"]),
            )
            source_id = int(existing["id"])
        else:
            await get_db().execute(
                """
                INSERT INTO streamers (
                    user_id, guild_id, platform, channel_url, channel_name, template, ping_role_id, active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_id,
                    payload.guild_id,
                    payload.platform,
                    *values,
                ),
            )
            row = await get_db().fetch_one("SELECT last_insert_rowid() AS id")
            source_id = int(row["id"])
        await get_db().commit()
        return {
            "id": source_id,
            "user_id": owner_id,
            "guild_id": payload.guild_id,
            "platform": payload.platform,
            "channel_url": payload.channel_url,
            "channel_name": payload.channel_name,
            "active": payload.active,
        }

    async def preview_alert(self, payload: CreatorAlertTestPayload, access_token: str) -> dict[str, Any]:
        logger.info("Previewing creator alert guild_id=%s platform=%s", payload.guild_id, payload.platform)
        _, access = await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "creator-alerts", "edit")
        if not (access["is_admin"] or access["is_streamer"]):
            raise HTTPException(status_code=403, detail="Creator or administrator access is required")
        return build_creator_alert_message(payload)

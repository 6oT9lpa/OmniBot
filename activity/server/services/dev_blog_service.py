import json
from typing import Any, Optional

from fastapi import HTTPException

from activity.server.dependencies import get_db
from activity.server.schemas.dev_blog import DevBlogPostPayload
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.audit_service import ActivityAuditService
from activity.server.services.channel_purpose_service import ChannelPurposeService
from activity.server.services.discord_service import DiscordService
from activity.server.utils.dev_blog_messages import build_dev_blog_message
from core.domain.channel_purpose import ChannelPurpose
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class DevBlogService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._audit_service = ActivityAuditService()
        self._channel_purpose_service = ChannelPurposeService()
        self._discord = DiscordService()

    async def list_posts(self, guild_id: int, limit: int, access_token: str) -> list[dict[str, Any]]:
        logger.info("Listing dev blog posts guild_id=%s limit=%s", guild_id, limit)
        await self._access_service.ensure_developer_or_admin(access_token, str(guild_id))
        return await get_db().fetch_all(
            """
            SELECT id, guild_id, channel_id, message_id, author_id, title,
                   payload_json, status, created_at, updated_at
            FROM dev_blog_posts
            WHERE guild_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (guild_id, limit),
        )

    async def create_post(self, payload: DevBlogPostPayload, access_token: str) -> dict[str, Any]:
        logger.info("Creating dev blog post guild_id=%s title=%s status=%s", payload.guild_id, payload.title, payload.status)
        user, _ = await self._access_service.ensure_developer_or_admin(access_token, str(payload.guild_id))
        if payload.status == "draft":
            draft_count = await get_db().fetch_one(
                "SELECT COUNT(*) AS total FROM dev_blog_posts WHERE guild_id = ? AND status = 'draft'",
                (payload.guild_id,),
            )
            if int(draft_count["total"]) >= 10:
                logger.warning("Dev blog draft limit reached guild_id=%s", payload.guild_id)
                raise HTTPException(status_code=400, detail="Dev Blog draft limit is 10")

        channel_id = await self._resolve_channel_id(payload)
        message_payload = build_dev_blog_message(payload)
        message_id: Optional[int] = None

        if payload.status == "published":
            logger.info("Publishing dev blog post to Discord guild_id=%s channel_id=%s", payload.guild_id, channel_id)
            message = await self._discord.bot_request(
                "POST",
                f"/channels/{channel_id}/messages",
                json_body=message_payload,
            )
            message_id = int(message["id"])

        await get_db().execute(
            """
            INSERT INTO dev_blog_posts (
                guild_id, channel_id, message_id, author_id, title, payload_json, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.guild_id,
                channel_id,
                message_id,
                int(user["id"]),
                payload.title,
                json.dumps(
                    {
                        "content": payload.content,
                        "embeds": [embed.model_dump() for embed in payload.embeds],
                        "image_render_mode": payload.image_render_mode,
                        "message": message_payload,
                    },
                    ensure_ascii=False,
                ),
                payload.status,
            ),
        )
        await get_db().commit()
        row = await get_db().fetch_one("SELECT last_insert_rowid() AS id")
        logger.info("Dev blog post saved guild_id=%s post_id=%s message_id=%s", payload.guild_id, row["id"], message_id)
        await self._audit_service.log_action(
            guild_id=payload.guild_id,
            actor_id=int(user["id"]),
            actor_name=self._display_name(user),
            target_id=int(row["id"]),
            target_name=payload.title,
            event_type="activity_dev_blog_published" if payload.status == "published" else "activity_dev_blog_draft_saved",
            details=f"Dev Blog post '{payload.title}' saved as {payload.status}.",
        )
        return {
            "id": int(row["id"]),
            "channel_id": channel_id,
            "message_id": message_id,
            "status": payload.status,
            "payload": message_payload,
        }

    async def _resolve_channel_id(self, payload: DevBlogPostPayload) -> int:
        if payload.status == "published":
            return await self._channel_purpose_service.get_required_purpose_channel(payload.guild_id, ChannelPurpose.DEV_BLOG)
        row = await get_db().fetch_one(
            "SELECT channel_id FROM server_channel_purposes WHERE guild_id = ? AND purpose = ?",
            (payload.guild_id, ChannelPurpose.DEV_BLOG.value),
        )
        return int(row["channel_id"]) if row else 0

    def _display_name(self, user: dict[str, Any]) -> str:
        return user.get("global_name") or user.get("username") or str(user.get("id"))

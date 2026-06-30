import re
from typing import Any

from fastapi import HTTPException

from activity.server.dependencies import get_db
from activity.server.schemas.welcome import WelcomeConfigPayload
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.audit_service import ActivityAuditService
from activity.server.services.channel_purpose_service import ChannelPurposeService
from activity.server.services.discord_service import DiscordService
from core.domain.channel_purpose import ChannelPurpose
from activity.server.utils.welcome_config import normalize_config
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityWelcomeService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._audit_service = ActivityAuditService()
        self._channel_purpose_service = ChannelPurposeService()
        self._discord = DiscordService()

    async def get_config(self, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Loading Activity welcome config guild_id=%s", guild_id)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "welcome")
        config = await get_db().fetch_one(
            "SELECT * FROM welcome_config WHERE guild_id = ?",
            (guild_id,),
        )
        return normalize_config(config, guild_id)

    async def save_config(self, payload: WelcomeConfigPayload, access_token: str) -> dict[str, Any]:
        logger.info("Saving Activity welcome config guild_id=%s", payload.guild_id)
        await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "welcome", "edit")
        db = get_db()
        values = (
            payload.guild_id,
            payload.title,
            payload.description,
            payload.thumbnail_url,
            payload.footer_text,
            payload.footer_icon_url,
            payload.color,
            1 if payload.is_enabled else 0,
            payload.rules_channel_id,
            payload.roles_channel_id,
        )
        await db.execute(
            """
            INSERT INTO welcome_config (
                guild_id, title, description, thumbnail_url, footer_text,
                footer_icon_url, color, is_enabled, rules_channel_id, roles_channel_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                thumbnail_url = excluded.thumbnail_url,
                footer_text = excluded.footer_text,
                footer_icon_url = excluded.footer_icon_url,
                color = excluded.color,
                is_enabled = excluded.is_enabled,
                rules_channel_id = excluded.rules_channel_id,
                roles_channel_id = excluded.roles_channel_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            values,
        )
        await db.commit()
        saved = await db.fetch_one(
            "SELECT * FROM welcome_config WHERE guild_id = ?",
            (payload.guild_id,),
        )
        return normalize_config(saved, payload.guild_id)

    async def reset_config(self, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Resetting Activity welcome config guild_id=%s", guild_id)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "welcome", "manage")
        db = get_db()
        await db.execute("DELETE FROM welcome_config WHERE guild_id = ?", (guild_id,))
        await db.commit()
        return normalize_config(None, guild_id)

    async def send_test_message(self, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Sending Activity welcome test message guild_id=%s", guild_id)
        actor, _ = await self._access_service.ensure_module_access(access_token, str(guild_id), "welcome", "edit")
        channel_id = await self._channel_purpose_service.get_required_purpose_channel(guild_id, ChannelPurpose.WELCOME)
        config = await self.get_config(guild_id, access_token)
        if not config.get("is_enabled"):
            raise HTTPException(status_code=400, detail="Welcome module is disabled")

        message = await self._discord.bot_request(
            "POST",
            f"/channels/{channel_id}/messages",
            json_body=self._build_test_payload(config, actor),
        )
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(actor["id"]),
            actor_name=self._display_name(actor),
            target_id=channel_id,
            event_type="activity_welcome_test_sent",
            details=f"Sent welcome test message to channel {channel_id}.",
        )
        return {"channel_id": channel_id, "message_id": int(message["id"]), "sent": True}

    def _build_test_payload(self, config: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        title = self._replace_placeholders(config.get("title") or "Welcome", actor)
        description = self._replace_placeholders(config.get("description") or "Welcome test message.", actor)
        embed: dict[str, Any] = {
            "title": title,
            "description": description,
            "color": int(config.get("color") or 0x5865F2),
        }
        if config.get("thumbnail_url"):
            embed["thumbnail"] = {"url": config["thumbnail_url"]}
        if config.get("footer_text"):
            embed["footer"] = {
                "text": self._replace_placeholders(config["footer_text"], actor),
                **({"icon_url": config["footer_icon_url"]} if config.get("footer_icon_url") else {}),
            }
        return {"content": "", "embeds": [embed], "allowed_mentions": {"parse": []}}

    def _replace_placeholders(self, value: str, actor: dict[str, Any]) -> str:
        display_name = actor.get("global_name") or actor.get("username") or "Discord user"
        replacements = {
            "{user}": display_name,
            "{user_name}": actor.get("username") or display_name,
            "{server}": "this Discord server",
            "{guild}": "this Discord server",
            "{member_count}": "current member count",
            "{joined_at}": "join date",
        }
        for key, replacement in replacements.items():
            value = value.replace(key, replacement)
        value = re.sub(r"\{channel\.(\d{15,25})\}", r"<#\1>", value)
        value = re.sub(r"\{role\.(\d{15,25})\}", r"<@&\1>", value)
        value = re.sub(r"\{user\.(\d{15,25})\}", r"<@\1>", value)
        logger.debug("Activity welcome test placeholders normalized actor_id=%s", actor.get("id"))
        return value

    def _display_name(self, user: dict[str, Any]) -> str:
        return user.get("global_name") or user.get("username") or str(user.get("id"))

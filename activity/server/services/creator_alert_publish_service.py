from typing import Any

from activity.server.dependencies import get_db, get_role_purpose_service
from activity.server.services.discord_service import DiscordService
from core.domain.channel_purpose import ChannelPurpose
from core.domain.creator_alert import CreatorContentEvent, CreatorPlatform
from core.domain.server_role_purpose import ServerRolePurpose
from infrastructure.api.kick_client import KickClient
from infrastructure.api.twitch_client import TwitchClient
from infrastructure.api.youtube_client import YouTubeClient
from infrastructure.config import get_config
from infrastructure.logging import get_logger
from presentation.embeds.creator_alert_embed import CreatorAlertEmbedBuilder


logger = get_logger(__name__)


class CreatorAlertPublishService:
    def __init__(self) -> None:
        self._discord = DiscordService()
        config = get_config()
        twitch_secret = (
            config.twitch_client_secret.get_secret_value()
            if config.twitch_client_secret
            else None
        )
        youtube_key = (
            config.youtube_api_key.get_secret_value()
            if config.youtube_api_key
            else None
        )
        self._platform_clients = {
            CreatorPlatform.TWITCH: TwitchClient(config.twitch_client_id, twitch_secret, config.discord_proxy_url),
            CreatorPlatform.YOUTUBE: YouTubeClient(youtube_key, config.discord_proxy_url),
            CreatorPlatform.KICK: KickClient(),
        }

    async def publish_saved_source_if_live(self, source: dict[str, Any]) -> None:
        channel_id = await self._stream_announce_channel_id(int(source["guild_id"]))
        if not channel_id:
            logger.info(
                "Creator alert immediate publish skipped because stream channel is not configured guild_id=%s source_id=%s",
                source["guild_id"],
                source["id"],
            )
            return

        platform = CreatorPlatform(source["platform"])
        client = self._platform_clients.get(platform)
        if not client or not getattr(client, "is_configured", True):
            logger.info(
                "Creator alert immediate publish skipped because platform is not configured platform=%s source_id=%s",
                source["platform"],
                source["id"],
            )
            return

        try:
            event = await client.fetch_latest_event(source["channel_url"], source.get("external_channel_id"))
        except Exception as exc:
            logger.error(
                "Creator alert immediate platform check failed source_id=%s platform=%s error=%s",
                source["id"],
                source["platform"],
                exc,
                exc_info=True,
            )
            return
        if not event:
            logger.info("Creator alert immediate publish found no live event source_id=%s", source["id"])
            return
        if source.get("last_event_id") == event.event_id:
            logger.info(
                "Creator alert immediate publish skipped duplicate source_id=%s event_id=%s",
                source["id"],
                event.event_id,
            )
            return

        message_payload = await self._build_live_message(source, event)
        message = await self._discord.safe_bot_request(
            "POST",
            f"/channels/{channel_id}/messages",
            json_body=message_payload,
        )
        if not message:
            logger.warning("Creator alert immediate publish was not accepted by Discord source_id=%s", source["id"])
            return
        await get_db().execute(
            """
            UPDATE creator_alert_subscriptions
            SET last_event_id = ?, last_checked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (event.event_id, int(source["id"])),
        )
        await get_db().commit()
        logger.info(
            "Creator alert immediate publish sent guild_id=%s source_id=%s event_id=%s message_id=%s",
            source["guild_id"],
            source["id"],
            event.event_id,
            message.get("id"),
        )

    async def _build_live_message(self, source: dict[str, Any], event: CreatorContentEvent) -> dict[str, Any]:
        ping_role_id = source.get("ping_role_id") or await get_role_purpose_service().get_role(
            int(source["guild_id"]),
            ServerRolePurpose.PING_STREAM,
        )
        creator_ping = f"||<@&{ping_role_id}>||" if ping_role_id else f"<@{source['user_id']}>"
        embed = CreatorAlertEmbedBuilder.build(
            event,
            title_template=source.get("title_template") or "",
            description_template=source.get("description_template") or "",
            color=CreatorAlertEmbedBuilder.platform_color(event.platform, source.get("color")),
            creator_ping=creator_ping,
            creator_icon_url=await self._creator_icon_url(int(source["guild_id"]), int(source["user_id"])),
        ).to_dict()
        message: dict[str, Any] = {
            "content": creator_ping if ping_role_id else "",
            "embeds": [embed],
            "allowed_mentions": {"roles": [str(ping_role_id)] if ping_role_id else []},
        }
        button = self._link_button(source.get("button_label") or "Watch", event.url)
        if button:
            message["components"] = [{"type": 1, "components": [button]}]
        return message

    async def _stream_announce_channel_id(self, guild_id: int) -> int | None:
        row = await get_db().fetch_one(
            """
            SELECT channel_id FROM server_channel_purposes
            WHERE guild_id = ? AND purpose = ?
            """,
            (guild_id, ChannelPurpose.STREAM_ANNOUNCE.value),
        )
        return int(row["channel_id"]) if row else None

    async def _creator_icon_url(self, guild_id: int, user_id: int) -> str | None:
        member = await self._discord.safe_bot_request("GET", f"/guilds/{guild_id}/members/{user_id}")
        if not member:
            return None
        user = member.get("user") or {}
        avatar = user.get("avatar")
        if not avatar:
            return None
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=128"

    def _link_button(self, label: str, url: str) -> dict[str, Any] | None:
        if not url.startswith(("http://", "https://")):
            return None
        return {
            "type": 2,
            "style": 5,
            "label": label[:80] or "Watch",
            "url": url,
        }

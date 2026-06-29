import time
from typing import Any, Literal, Optional

import httpx
from fastapi import HTTPException

from activity.server.config import activity_server_config
from activity.server.schemas.discord import DiscordChannel, DiscordMember, DiscordRole
from activity.server.utils.http_client import discord_async_client
from infrastructure.config import get_config
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class DiscordService:
    async def bot_request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        token = get_config().discord_token.get_secret_value()
        headers = {"Authorization": f"Bot {token}"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        started = time.perf_counter()
        logger.info("Discord bot request started method=%s path=%s", method, path)
        async with discord_async_client(timeout=15) as client:
            response = await client.request(
                method,
                f"{activity_server_config.discord_api_base}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "Discord bot request completed method=%s path=%s status=%s elapsed_ms=%s",
            method,
            path,
            response.status_code,
            elapsed_ms,
        )
        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            logger.warning("Discord bot request failed method=%s path=%s status=%s body=%s", method, path, response.status_code, response.text)
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

    async def safe_bot_request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        try:
            return await self.bot_request(method, path, params=params, json_body=json_body)
        except HTTPException as exc:
            logger.warning("Safe Discord request suppressed method=%s path=%s status=%s", method, path, exc.status_code)
            return None

    async def list_channels(self, guild_id: str, kind: Optional[Literal["text", "voice"]] = None) -> list[DiscordChannel]:
        logger.info("Listing Discord channels guild_id=%s kind=%s", guild_id, kind or "all")
        channel_types = {"text": 0, "voice": 2}
        channels = await self.bot_request("GET", f"/guilds/{guild_id}/channels")
        if kind:
            channels = [channel for channel in channels if channel.get("type") == channel_types[kind]]
        return [
            DiscordChannel(
                id=channel["id"],
                name=channel.get("name", "unknown"),
                type=channel.get("type", 0),
                position=channel.get("position", 0),
                parent_id=channel.get("parent_id"),
            )
            for channel in sorted(channels, key=lambda item: (item.get("position", 0), item.get("name", "")))
        ]

    async def list_roles(self, guild_id: str) -> list[DiscordRole]:
        logger.info("Listing Discord roles guild_id=%s", guild_id)
        roles = await self.bot_request("GET", f"/guilds/{guild_id}/roles")
        return [
            DiscordRole(
                id=role["id"],
                name=role.get("name", "unknown"),
                color=role.get("color", 0),
                position=role.get("position", 0),
                permissions=int(role.get("permissions") or 0),
                managed=role.get("managed", False),
                mentionable=role.get("mentionable", False),
            )
            for role in sorted(roles, key=lambda item: item.get("position", 0), reverse=True)
        ]

    async def search_members(self, guild_id: str, query: str, limit: int) -> list[DiscordMember]:
        query = query.strip()
        if not query:
            logger.info("Skipping empty Discord member search guild_id=%s", guild_id)
            return []
        logger.info("Searching Discord members guild_id=%s query=%s limit=%s", guild_id, query, limit)
        members = await self.bot_request(
            "GET",
            f"/guilds/{guild_id}/members/search",
            params={"query": query, "limit": limit},
        )
        return [
            DiscordMember(
                id=member["user"]["id"],
                username=member["user"].get("username", "unknown"),
                display_name=member.get("nick")
                or member["user"].get("global_name")
                or member["user"].get("username", "unknown"),
                avatar=member["user"].get("avatar"),
            )
            for member in members
        ]

    async def list_members(self, guild_id: str, limit: int = 1000) -> list[DiscordMember]:
        logger.info("Listing Discord members guild_id=%s limit=%s", guild_id, limit)
        members = await self.bot_request(
            "GET",
            f"/guilds/{guild_id}/members",
            params={"limit": min(max(limit, 1), 1000)},
        )
        return [
            DiscordMember(
                id=member["user"]["id"],
                username=member["user"].get("username", "unknown"),
                display_name=member.get("nick")
                or member["user"].get("global_name")
                or member["user"].get("username", "unknown"),
                avatar=member["user"].get("avatar"),
            )
            for member in sorted(members, key=lambda item: (item.get("nick") or item["user"].get("global_name") or item["user"].get("username", "")).lower())
            if not member["user"].get("bot", False)
        ]

    async def fetch_member_role_ids(self, guild_id: str, user_id: str) -> set[int]:
        logger.info("Fetching Discord member roles guild_id=%s user_id=%s", guild_id, user_id)
        response = await self.safe_bot_request("GET", f"/guilds/{guild_id}/members/{user_id}")
        if not response:
            logger.warning("Discord member roles unavailable guild_id=%s user_id=%s", guild_id, user_id)
            return set()
        return {int(role_id) for role_id in response.get("roles", [])}

    async def measure_latency(self) -> Optional[int]:
        token = get_config().discord_token.get_secret_value()
        headers = {"Authorization": f"Bot {token}"}
        started = time.perf_counter()
        try:
            async with discord_async_client(timeout=10) as client:
                response = await client.get(f"{activity_server_config.discord_api_base}/gateway", headers=headers)
            if response.status_code >= 400:
                logger.warning("Discord latency probe failed status=%s", response.status_code)
                return None
        except httpx.HTTPError:
            logger.exception("Discord latency probe raised HTTP error")
            return None
        latency = round((time.perf_counter() - started) * 1000)
        logger.info("Discord latency measured latency_ms=%s", latency)
        return latency

import time
from typing import Any, Literal, Optional

import httpx
from fastapi import HTTPException

from activity.server.config import activity_server_config
from activity.server.schemas.discord import DiscordChannel, DiscordMember, DiscordRole
from infrastructure.config import get_config


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

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(
                method,
                f"{activity_server_config.discord_api_base}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )

        if response.status_code == 204:
            return None
        if response.status_code >= 400:
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
        except HTTPException:
            return None

    async def list_channels(self, guild_id: str, kind: Optional[Literal["text", "voice"]] = None) -> list[DiscordChannel]:
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
            return []
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

    async def fetch_member_role_ids(self, guild_id: str, user_id: str) -> set[int]:
        response = await self.safe_bot_request("GET", f"/guilds/{guild_id}/members/{user_id}")
        if not response:
            return set()
        return {int(role_id) for role_id in response.get("roles", [])}

    async def measure_latency(self) -> Optional[int]:
        token = get_config().discord_token.get_secret_value()
        headers = {"Authorization": f"Bot {token}"}
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{activity_server_config.discord_api_base}/gateway", headers=headers)
            if response.status_code >= 400:
                return None
        except httpx.HTTPError:
            return None
        return round((time.perf_counter() - started) * 1000)

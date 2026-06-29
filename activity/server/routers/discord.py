from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from activity.server.dependencies import require_bearer_token
from activity.server.schemas.discord import DiscordChannel, DiscordMember, DiscordRole
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.discord_service import DiscordService

router = APIRouter()
access_service = ActivityAccessService()
service = DiscordService()


@router.get("/api/discord/channels", response_model=list[DiscordChannel])
async def list_discord_channels(
    guild_id: str = Query(min_length=1),
    kind: Optional[Literal["text", "voice"]] = None,
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordChannel]:
    await access_service.ensure_panel_access(access_token, guild_id)
    return await service.list_channels(guild_id, kind)


@router.get("/api/discord/roles", response_model=list[DiscordRole])
async def list_discord_roles(
    guild_id: str = Query(min_length=1),
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordRole]:
    await access_service.ensure_admin(access_token, guild_id)
    return await service.list_roles(guild_id)


@router.get("/api/discord/members/search", response_model=list[DiscordMember])
async def search_discord_members(
    guild_id: str = Query(min_length=1),
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordMember]:
    await access_service.ensure_panel_access(access_token, guild_id)
    return await service.search_members(guild_id, q, limit)


@router.get("/api/discord/members", response_model=list[DiscordMember])
async def list_discord_members(
    guild_id: str = Query(min_length=1),
    limit: int = Query(default=1000, ge=1, le=1000),
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordMember]:
    await access_service.ensure_panel_access(access_token, guild_id)
    return await service.list_members(guild_id, limit)

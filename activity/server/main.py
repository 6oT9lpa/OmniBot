import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from application.services import ServerRolePurposeService
from application.schemas.server_role_purpose_schemas import ServerRolePurposeSchema
from core.domain.activity_user_type import ActivityUserType
from core.domain.channel_purpose import ChannelPurpose
from core.domain.server_role_purpose import ServerRolePurpose
from infrastructure.config import get_config
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories import ServerRolePurposeRepository

DISCORD_API_BASE = "https://discord.com/api/v10"
ADMINISTRATOR = 0x0000000000000008
ROOT_DIR = Path(__file__).resolve().parents[2]
CLIENT_DIST = ROOT_DIR / "activity" / "client" / "dist"

app = FastAPI(title="Omnibot Activity API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_db: Optional[DatabaseManager] = None
_role_purpose_service: Optional[ServerRolePurposeService] = None


class TokenRequest(BaseModel):
    code: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class ActivityUser(BaseModel):
    id: str
    username: str
    discriminator: Optional[str] = None
    global_name: Optional[str] = None
    avatar: Optional[str] = None


class ActivityAccess(BaseModel):
    is_admin: bool
    is_streamer: bool
    is_developer: bool


class ActivitySession(BaseModel):
    user: ActivityUser
    guild_id: str
    user_type: ActivityUserType
    access: ActivityAccess
    is_admin: bool


class WelcomeConfigPayload(BaseModel):
    guild_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    footer_text: Optional[str] = None
    footer_icon_url: Optional[str] = None
    color: Optional[int] = None
    is_enabled: bool = True
    rules_channel_id: Optional[int] = None
    roles_channel_id: Optional[int] = None


class ActivityRolePayload(BaseModel):
    guild_id: int = Field(gt=0)
    purpose: ServerRolePurpose
    role_id: int = Field(gt=0)


class ActivityHealthSignal(BaseModel):
    name: str
    value: str
    status: str
    latency_ms: Optional[int] = None


class ActivityHealthResponse(BaseModel):
    guild_id: str
    signals: list[ActivityHealthSignal]
    bot_latency_ms: Optional[int] = None


class DiscordChannel(BaseModel):
    id: str
    name: str
    type: int
    position: int = 0
    parent_id: Optional[str] = None


class DiscordRole(BaseModel):
    id: str
    name: str
    color: int = 0
    position: int = 0
    managed: bool = False
    mentionable: bool = False


class DiscordMember(BaseModel):
    id: str
    username: str
    display_name: str
    avatar: Optional[str] = None


class ChannelPurposePayload(BaseModel):
    guild_id: int = Field(gt=0)
    purpose: ChannelPurpose
    channel_id: int = Field(gt=0)


class DevBlogEmbedPayload(BaseModel):
    title: Optional[str] = Field(default=None, max_length=256)
    description: str = Field(min_length=1, max_length=4096)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    color: int = Field(default=0x5865F2, ge=0, le=0xFFFFFF)


class DevBlogPostPayload(BaseModel):
    guild_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    content: Optional[str] = Field(default=None, max_length=2000)
    embeds: list[DevBlogEmbedPayload] = Field(min_length=1, max_length=10)
    status: Literal["draft", "published"] = "published"


class CreatorAlertSourcePayload(BaseModel):
    guild_id: int = Field(gt=0)
    platform: Literal["twitch", "youtube", "kick"]
    channel_url: str = Field(min_length=1, max_length=2048)
    channel_name: Optional[str] = Field(default=None, max_length=120)
    template: Optional[str] = Field(default=None, max_length=2000)
    ping_role_id: Optional[int] = Field(default=None, gt=0)
    active: bool = True
    user_id: Optional[int] = Field(default=None, gt=0)


class CreatorAlertTestPayload(BaseModel):
    guild_id: int = Field(gt=0)
    platform: Literal["twitch", "youtube", "kick"]
    channel_name: str = Field(min_length=1, max_length=120)
    channel_url: str = Field(min_length=1, max_length=2048)
    template: Optional[str] = Field(default=None, max_length=2000)
    ping_role_id: Optional[int] = Field(default=None, gt=0)


class VoiceRoomUpdatePayload(BaseModel):
    guild_id: int = Field(gt=0)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_limit: Optional[int] = Field(default=None, ge=0, le=99)
    locked: Optional[bool] = None
    owner_id: Optional[int] = Field(default=None, gt=0)
    persistent: Optional[bool] = None


@app.on_event("startup")
async def startup() -> None:
    global _db, _role_purpose_service
    config = get_config()
    _db = DatabaseManager(config.database_url)
    await _db.initialize()
    _role_purpose_service = ServerRolePurposeService(ServerRolePurposeRepository(_db))


@app.on_event("shutdown")
async def shutdown() -> None:
    if _db:
        await _db.close()


@app.post("/api/auth/token", response_model=TokenResponse)
async def exchange_token(payload: TokenRequest) -> dict[str, Any]:
    client_id = os.getenv("DISCORD_CLIENT_ID")
    client_secret = os.getenv("DISCORD_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET are required",
        )

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": payload.code,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    token = response.json()
    return {
        "access_token": token["access_token"],
        "token_type": token.get("token_type", "Bearer"),
        "expires_in": token.get("expires_in", 0),
        "scope": token.get("scope", ""),
    }


def require_bearer_token(authorization: str = Header(default="")) -> str:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Bearer token is required")
    return authorization[len(prefix):].strip()


@app.get("/api/activity/session", response_model=ActivitySession)
async def get_activity_session(
    guild_id: str = Query(min_length=1),
    access_token: str = Depends(require_bearer_token),
) -> ActivitySession:
    user, access = await fetch_user_and_access_state(access_token, guild_id)
    return ActivitySession(
        user=ActivityUser(**user),
        guild_id=guild_id,
        user_type=resolve_user_type(access),
        access=ActivityAccess(**access),
        is_admin=access["is_admin"],
    )


@app.get("/api/welcome/config")
async def get_welcome_config(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_admin(access_token, str(guild_id))
    db = get_db()
    config = await db.fetch_one(
        "SELECT * FROM welcome_config WHERE guild_id = ?",
        (guild_id,),
    )
    return normalize_config(config, guild_id)


@app.put("/api/welcome/config")
async def save_welcome_config(
    payload: WelcomeConfigPayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_admin(access_token, str(payload.guild_id))
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


@app.delete("/api/welcome/config")
async def reset_welcome_config(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_admin(access_token, str(guild_id))
    db = get_db()
    await db.execute("DELETE FROM welcome_config WHERE guild_id = ?", (guild_id,))
    await db.commit()
    return normalize_config(None, guild_id)


@app.get("/api/activity/roles")
async def get_activity_roles(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, int]:
    await ensure_admin(access_token, str(guild_id))
    return await get_role_purpose_service().get_all_roles(guild_id)


@app.put("/api/activity/roles")
async def save_activity_role(
    payload: ActivityRolePayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, int]:
    await ensure_admin(access_token, str(payload.guild_id))
    validated = ServerRolePurposeSchema.model_validate(payload.model_dump())
    await get_role_purpose_service().set_role(
        validated.guild_id,
        validated.purpose,
        validated.role_id,
    )
    return await get_role_purpose_service().get_all_roles(validated.guild_id)


@app.get("/api/discord/channels", response_model=list[DiscordChannel])
async def list_discord_channels(
    guild_id: str = Query(min_length=1),
    kind: Optional[Literal["text", "voice"]] = None,
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordChannel]:
    await ensure_panel_access(access_token, guild_id)
    channel_types = {"text": 0, "voice": 2}
    channels = await discord_bot_request("GET", f"/guilds/{guild_id}/channels")
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


@app.get("/api/discord/roles", response_model=list[DiscordRole])
async def list_discord_roles(
    guild_id: str = Query(min_length=1),
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordRole]:
    await ensure_admin(access_token, guild_id)
    roles = await discord_bot_request("GET", f"/guilds/{guild_id}/roles")
    return [
        DiscordRole(
            id=role["id"],
            name=role.get("name", "unknown"),
            color=role.get("color", 0),
            position=role.get("position", 0),
            managed=role.get("managed", False),
            mentionable=role.get("mentionable", False),
        )
        for role in sorted(roles, key=lambda item: item.get("position", 0), reverse=True)
    ]


@app.get("/api/discord/members/search", response_model=list[DiscordMember])
async def search_discord_members(
    guild_id: str = Query(min_length=1),
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
    access_token: str = Depends(require_bearer_token),
) -> list[DiscordMember]:
    await ensure_panel_access(access_token, guild_id)
    query = q.strip()
    if not query:
        return []
    members = await discord_bot_request(
        "GET",
        f"/guilds/{guild_id}/members/search",
        params={"query": query, "limit": limit},
    )
    return [
        DiscordMember(
            id=member["user"]["id"],
            username=member["user"].get("username", "unknown"),
            display_name=member.get("nick") or member["user"].get("global_name") or member["user"].get("username", "unknown"),
            avatar=member["user"].get("avatar"),
        )
        for member in members
    ]


@app.get("/api/activity/channel-purposes")
async def get_channel_purposes(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, int]:
    await ensure_panel_access(access_token, str(guild_id))
    rows = await get_db().fetch_all(
        "SELECT purpose, channel_id FROM server_channel_purposes WHERE guild_id = ?",
        (guild_id,),
    )
    return {row["purpose"]: int(row["channel_id"]) for row in rows}


@app.put("/api/activity/channel-purposes")
async def save_channel_purpose(
    payload: ChannelPurposePayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, int]:
    await ensure_admin(access_token, str(payload.guild_id))
    await get_db().execute(
        """
        INSERT INTO server_channel_purposes (guild_id, purpose, channel_id)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, purpose) DO UPDATE SET
            channel_id = excluded.channel_id,
            updated_at = CURRENT_TIMESTAMP
        """,
        (payload.guild_id, payload.purpose.value, payload.channel_id),
    )
    await get_db().commit()
    return await get_channel_purposes(payload.guild_id, access_token)


@app.get("/api/dev-blog/posts")
async def list_dev_blog_posts(
    guild_id: int = Query(gt=0),
    limit: int = Query(default=25, ge=1, le=100),
    access_token: str = Depends(require_bearer_token),
) -> list[dict[str, Any]]:
    await ensure_developer_or_admin(access_token, str(guild_id))
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


@app.post("/api/dev-blog/posts")
async def create_dev_blog_post(
    payload: DevBlogPostPayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    user, _ = await ensure_developer_or_admin(access_token, str(payload.guild_id))
    channel_id = await get_required_purpose_channel(payload.guild_id, ChannelPurpose.DEV_BLOG)
    message_payload = build_dev_blog_message(payload)
    message_id: Optional[int] = None

    if payload.status == "published":
        message = await discord_bot_request(
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
            json.dumps(message_payload, ensure_ascii=False),
            payload.status,
        ),
    )
    await get_db().commit()
    row = await get_db().fetch_one("SELECT last_insert_rowid() AS id")
    return {
        "id": int(row["id"]),
        "channel_id": channel_id,
        "message_id": message_id,
        "status": payload.status,
        "payload": message_payload,
    }


@app.get("/api/creator-alerts/sources")
async def list_creator_alert_sources(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> list[dict[str, Any]]:
    user, access = await fetch_user_and_access_state(access_token, str(guild_id))
    if not (access["is_admin"] or access["is_streamer"]):
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


@app.put("/api/creator-alerts/sources")
async def save_creator_alert_source(
    payload: CreatorAlertSourcePayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    user, access = await fetch_user_and_access_state(access_token, str(payload.guild_id))
    if not (access["is_admin"] or access["is_streamer"]):
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


@app.post("/api/creator-alerts/test")
async def preview_creator_alert(
    payload: CreatorAlertTestPayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    user, access = await fetch_user_and_access_state(access_token, str(payload.guild_id))
    if not (access["is_admin"] or access["is_streamer"]):
        raise HTTPException(status_code=403, detail="Creator or administrator access is required")
    return build_creator_alert_message(payload)


@app.get("/api/voice/rooms")
async def list_voice_rooms(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> list[dict[str, Any]]:
    await ensure_panel_access(access_token, str(guild_id))
    rooms = await get_db().fetch_all(
        "SELECT * FROM voice_rooms WHERE guild_id = ? ORDER BY created_at DESC",
        (guild_id,),
    )
    results = []
    for room in rooms:
        channel = await safe_discord_bot_request("GET", f"/channels/{room['channel_id']}")
        results.append({**room, "discord": channel})
    return results


@app.patch("/api/voice/rooms/{channel_id}")
async def update_voice_room(
    channel_id: int,
    payload: VoiceRoomUpdatePayload,
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_panel_access(access_token, str(payload.guild_id))
    patch: dict[str, Any] = {}
    if payload.name is not None:
        patch["name"] = payload.name
    if payload.user_limit is not None:
        patch["user_limit"] = payload.user_limit
    if payload.locked is not None:
        patch["permission_overwrites"] = await build_voice_lock_overwrites(payload.guild_id, channel_id, payload.locked)
    if patch:
        await discord_bot_request("PATCH", f"/channels/{channel_id}", json_body=patch)
    if payload.owner_id is not None:
        await get_db().execute("UPDATE voice_rooms SET owner_id = ? WHERE channel_id = ?", (payload.owner_id, channel_id))
    if payload.persistent is not None:
        await get_db().execute("UPDATE voice_rooms SET is_persistent = ? WHERE channel_id = ?", (1 if payload.persistent else 0, channel_id))
    await get_db().commit()
    return {"channel_id": channel_id, "updated": True}


@app.delete("/api/voice/rooms/{channel_id}")
async def delete_voice_room(
    channel_id: int,
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_admin(access_token, str(guild_id))
    await safe_discord_bot_request("DELETE", f"/channels/{channel_id}")
    await get_db().execute("DELETE FROM voice_rooms WHERE channel_id = ?", (channel_id,))
    await get_db().commit()
    return {"channel_id": channel_id, "deleted": True}


@app.get("/api/stats/server")
async def get_activity_server_stats(
    guild_id: int = Query(gt=0),
    period: int = Query(default=7, ge=1, le=365),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_panel_access(access_token, str(guild_id))
    return {
        "summary": await query_server_stats(guild_id, period),
        "channels": await query_channel_stats(guild_id, period),
        "hourly": await query_hourly_stats(guild_id, period),
    }


@app.get("/api/stats/users/search")
async def search_activity_user_stats(
    guild_id: int = Query(gt=0),
    q: str = Query(default="", max_length=100),
    access_token: str = Depends(require_bearer_token),
) -> list[dict[str, Any]]:
    await ensure_panel_access(access_token, str(guild_id))
    members = await search_discord_members(str(guild_id), q, 10, access_token)
    stats = []
    for member in members:
        row = await get_db().fetch_one(
            "SELECT * FROM user_stats WHERE guild_id = ? AND user_id = ?",
            (guild_id, int(member.id)),
        )
        stats.append({"member": member.model_dump(), "stats": row})
    return stats


@app.get("/api/logs")
async def list_activity_logs(
    guild_id: int = Query(gt=0),
    source: Literal["messages", "audit", "all"] = "all",
    event_type: Optional[str] = None,
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, list[dict[str, Any]]]:
    await ensure_panel_access(access_token, str(guild_id))
    return {
        "messages": [] if source == "audit" else await query_message_logs(guild_id, event_type, q, limit),
        "audit": [] if source == "messages" else await query_audit_logs(guild_id, event_type, q, limit),
    }


@app.get("/api/bot/settings")
async def get_bot_settings(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_admin(access_token, str(guild_id))
    config = get_config()
    return {
        "guild_id": guild_id,
        "command_prefix": config.command_prefix,
        "activity_name": config.activity_name,
        "bot_status": config.bot_status,
        "activity_rotation_enabled": config.activity_rotation_enabled,
        "activity_rotation_interval_seconds": config.activity_rotation_interval_seconds,
        "log_level": config.log_level,
        "retention": {
            "message_log_retention_days": config.message_log_retention_days,
            "punishment_retention_days": config.punishment_retention_days,
        },
        "channel_purposes": await get_channel_purposes(guild_id, access_token),
    }


@app.get("/api/integrations")
async def get_integrations(
    guild_id: int = Query(gt=0),
    access_token: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    await ensure_panel_access(access_token, str(guild_id))
    sources = await get_db().fetch_all(
        """
        SELECT platform, COUNT(*) AS count, SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active_count
        FROM streamers
        WHERE guild_id = ?
        GROUP BY platform
        """,
        (guild_id,),
    )
    return {
        "discord": {"status": "connected"},
        "creator_platforms": sources,
        "ollama": {"status": "configured_by_bot_service"},
        "database": {"status": "connected"},
    }


@app.get("/api/activity/health", response_model=ActivityHealthResponse)
async def get_activity_health(
    guild_id: str = Query(min_length=1),
    access_token: str = Depends(require_bearer_token),
) -> ActivityHealthResponse:
    await fetch_user_and_access_state(access_token, guild_id)

    discord_latency = await measure_discord_latency()
    database_latency = await measure_database_latency()

    return ActivityHealthResponse(
        guild_id=guild_id,
        bot_latency_ms=discord_latency,
        signals=[
            ActivityHealthSignal(
                name="Discord API",
                value=f"{discord_latency} ms" if discord_latency is not None else "Unavailable",
                status="operational" if discord_latency is not None else "degraded",
                latency_ms=discord_latency,
            ),
            ActivityHealthSignal(
                name="Activity API",
                value="Serving",
                status="operational",
            ),
            ActivityHealthSignal(
                name="SQLite",
                value=f"{database_latency} ms" if database_latency is not None else "Unavailable",
                status="operational" if database_latency is not None else "degraded",
                latency_ms=database_latency,
            ),
            ActivityHealthSignal(
                name="Ollama",
                value="Configured by bot service",
                status="degraded",
            ),
            ActivityHealthSignal(
                name="Stream Checker",
                value="Configured by bot service",
                status="degraded",
            ),
        ],
    )


async def ensure_panel_access(access_token: str, guild_id: str) -> tuple[dict[str, Any], dict[str, bool]]:
    user, access = await fetch_user_and_access_state(access_token, guild_id)
    if not (access["is_admin"] or access["is_streamer"] or access["is_developer"]):
        raise HTTPException(status_code=403, detail="Activity module access is required")
    return user, access


async def ensure_developer_or_admin(access_token: str, guild_id: str) -> tuple[dict[str, Any], dict[str, bool]]:
    user, access = await fetch_user_and_access_state(access_token, guild_id)
    if not (access["is_admin"] or access["is_developer"]):
        raise HTTPException(status_code=403, detail="Developer or administrator access is required")
    return user, access


async def discord_bot_request(
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
            f"{DISCORD_API_BASE}{path}",
            params=params,
            json=json_body,
            headers=headers,
        )

    if response.status_code == 204:
        return None
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def safe_discord_bot_request(
    method: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
) -> Any:
    try:
        return await discord_bot_request(method, path, params=params, json_body=json_body)
    except HTTPException:
        return None


async def get_required_purpose_channel(guild_id: int, purpose: ChannelPurpose) -> int:
    row = await get_db().fetch_one(
        """
        SELECT channel_id FROM server_channel_purposes
        WHERE guild_id = ? AND purpose = ?
        """,
        (guild_id, purpose.value),
    )
    if not row:
        raise HTTPException(
            status_code=400,
            detail=f"Channel purpose '{purpose.value}' is not configured",
        )
    return int(row["channel_id"])


def build_dev_blog_message(payload: DevBlogPostPayload) -> dict[str, Any]:
    return {
        "content": payload.content or "",
        "embeds": [
            {
                "title": embed.title or payload.title,
                "description": embed.description,
                "color": embed.color,
                **({"image": {"url": embed.image_url}} if embed.image_url else {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for embed in payload.embeds
        ],
        "allowed_mentions": {"parse": []},
    }


def build_creator_alert_message(payload: CreatorAlertTestPayload) -> dict[str, Any]:
    title = {
        "twitch": "Stream is live",
        "youtube": "New video published",
        "kick": "Kick stream is live",
    }[payload.platform]
    template = payload.template or "{creator} is active on {platform}: {url}"
    description = template.format(
        creator=payload.channel_name,
        platform=payload.platform.title(),
        url=payload.channel_url,
    )
    content = f"<@&{payload.ping_role_id}>" if payload.ping_role_id else ""
    return {
        "content": content,
        "embeds": [
            {
                "title": title,
                "description": description,
                "url": payload.channel_url,
                "color": 0x5865F2,
            }
        ],
        "allowed_mentions": {"roles": [str(payload.ping_role_id)] if payload.ping_role_id else []},
    }


async def build_voice_lock_overwrites(guild_id: int, channel_id: int, locked: bool) -> list[dict[str, Any]]:
    channel = await discord_bot_request("GET", f"/channels/{channel_id}")
    overwrites = list(channel.get("permission_overwrites", []))
    everyone_id = str(guild_id)
    connect_bit = 0x00100000
    matched = False
    for overwrite in overwrites:
        if overwrite.get("id") == everyone_id and overwrite.get("type") == 0:
            allow = int(overwrite.get("allow", "0"))
            deny = int(overwrite.get("deny", "0"))
            if locked:
                deny |= connect_bit
                allow &= ~connect_bit
            else:
                allow |= connect_bit
                deny &= ~connect_bit
            overwrite["allow"] = str(allow)
            overwrite["deny"] = str(deny)
            matched = True
            break
    if not matched:
        overwrites.append(
            {
                "id": everyone_id,
                "type": 0,
                "allow": "0" if locked else str(connect_bit),
                "deny": str(connect_bit) if locked else "0",
            }
        )
    return overwrites


async def query_server_stats(guild_id: int, period: int) -> dict[str, Any]:
    cutoff = f"-{period} days"
    messages = await get_db().fetch_one(
        """
        SELECT COUNT(*) AS total_messages,
               COUNT(DISTINCT user_id) AS active_users,
               COUNT(DISTINCT channel_id) AS active_channels
        FROM messages
        WHERE guild_id = ? AND timestamp >= datetime('now', 'localtime', ?) AND deleted = 0
        """,
        (guild_id, cutoff),
    )
    voice = await get_db().fetch_one(
        """
        SELECT COUNT(DISTINCT user_id) AS voice_users,
               SUM(voice_minutes) AS total_voice_minutes
        FROM user_stats
        WHERE guild_id = ? AND voice_minutes > 0
        """,
        (guild_id,),
    )
    joins = await get_db().fetch_one(
        """
        SELECT SUM(CASE WHEN event_type = 'member_join' THEN 1 ELSE 0 END) AS joins,
               SUM(CASE WHEN event_type = 'member_leave' THEN 1 ELSE 0 END) AS leaves
        FROM guild_event_logs
        WHERE guild_id = ? AND created_at >= datetime('now', 'localtime', ?)
        """,
        (guild_id, cutoff),
    )
    return {
        **(messages or {}),
        **{f"voice_{key}": value for key, value in (voice or {}).items()},
        **(joins or {}),
        "period_days": period,
    }


async def query_channel_stats(guild_id: int, period: int) -> list[dict[str, Any]]:
    rows = await get_db().fetch_all(
        """
        SELECT channel_id, COUNT(*) AS messages
        FROM messages
        WHERE guild_id = ? AND timestamp >= datetime('now', 'localtime', ?) AND deleted = 0
        GROUP BY channel_id
        ORDER BY messages DESC
        LIMIT 100
        """,
        (guild_id, f"-{period} days"),
    )
    channels = {channel["id"]: channel for channel in await safe_discord_bot_request("GET", f"/guilds/{guild_id}/channels") or []}
    return [
        {
            **row,
            "channel_name": channels.get(str(row["channel_id"]), {}).get("name", str(row["channel_id"])),
        }
        for row in rows
    ]


async def query_hourly_stats(guild_id: int, period: int) -> list[dict[str, int]]:
    rows = await get_db().fetch_all(
        """
        SELECT CAST(substr(timestamp, 12, 2) AS INTEGER) AS hour, COUNT(*) AS count
        FROM messages
        WHERE guild_id = ? AND timestamp >= datetime('now', 'localtime', ?) AND deleted = 0
        GROUP BY hour
        ORDER BY hour
        """,
        (guild_id, f"-{period} days"),
    )
    values = {hour: 0 for hour in range(24)}
    for row in rows:
        values[int(row["hour"])] = int(row["count"])
    return [{"hour": hour, "count": count} for hour, count in values.items()]


async def query_message_logs(
    guild_id: int,
    event_type: Optional[str],
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    clauses = ["guild_id = ?"]
    params: list[Any] = [guild_id]
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if query.strip():
        clauses.append("(content LIKE ? OR author_name LIKE ?)")
        like = f"%{query.strip()}%"
        params.extend([like, like])
    params.append(limit)
    return await get_db().fetch_all(
        f"""
        SELECT * FROM message_logs
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        tuple(params),
    )


async def query_audit_logs(
    guild_id: int,
    event_type: Optional[str],
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    clauses = ["guild_id = ?"]
    params: list[Any] = [guild_id]
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if query.strip():
        clauses.append("(details LIKE ? OR actor_name LIKE ? OR target_name LIKE ?)")
        like = f"%{query.strip()}%"
        params.extend([like, like, like])
    params.append(limit)
    return await get_db().fetch_all(
        f"""
        SELECT * FROM guild_event_logs
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        tuple(params),
    )


async def ensure_admin(access_token: str, guild_id: str) -> None:
    _, access = await fetch_user_and_access_state(access_token, guild_id)
    if not access["is_admin"]:
        raise HTTPException(status_code=403, detail="Administrator permission is required")


async def fetch_user_and_access_state(access_token: str, guild_id: str) -> tuple[dict[str, Any], dict[str, bool]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        user_response = await client.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
        guilds_response = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=headers)

    if user_response.status_code >= 400:
        raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
    if guilds_response.status_code >= 400:
        raise HTTPException(status_code=guilds_response.status_code, detail=guilds_response.text)

    user = user_response.json()
    guilds = guilds_response.json()
    current_guild = next((guild for guild in guilds if guild.get("id") == guild_id), None)
    if current_guild is None:
        raise HTTPException(status_code=403, detail="User is not a member of this guild")

    permissions = int(current_guild.get("permissions") or 0)
    member_role_ids = await fetch_member_role_ids(guild_id, user["id"])
    role_purposes = await get_role_purpose_service().get_all_roles(int(guild_id))

    admin_role_id = role_purposes.get(ServerRolePurpose.ACTIVITY_ADMIN.value)
    streamer_role_id = role_purposes.get(ServerRolePurpose.ACTIVITY_STREAMER.value)
    developer_role_id = role_purposes.get(ServerRolePurpose.ACTIVITY_DEVELOPER.value)

    access = {
        "is_admin": bool(permissions & ADMINISTRATOR)
        or bool(admin_role_id and admin_role_id in member_role_ids),
        "is_streamer": bool(streamer_role_id and streamer_role_id in member_role_ids),
        "is_developer": bool(developer_role_id and developer_role_id in member_role_ids),
    }

    return user, access


async def fetch_member_role_ids(guild_id: str, user_id: str) -> set[int]:
    config = get_config()
    token = config.discord_token.get_secret_value()
    headers = {"Authorization": f"Bot {token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}",
            headers=headers,
        )

    if response.status_code >= 400:
        return set()

    member = response.json()
    return {int(role_id) for role_id in member.get("roles", [])}


async def measure_discord_latency() -> Optional[int]:
    token = get_config().discord_token.get_secret_value()
    headers = {"Authorization": f"Bot {token}"}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{DISCORD_API_BASE}/gateway", headers=headers)
        if response.status_code >= 400:
            return None
    except httpx.HTTPError:
        return None
    return round((time.perf_counter() - started) * 1000)


async def measure_database_latency() -> Optional[int]:
    started = time.perf_counter()
    try:
        await get_db().fetch_one("SELECT 1 AS ok")
    except Exception:
        return None
    return round((time.perf_counter() - started) * 1000)


def resolve_user_type(access: dict[str, bool]) -> ActivityUserType:
    if access["is_admin"]:
        return ActivityUserType.ADMIN
    if access["is_developer"]:
        return ActivityUserType.DEVELOPER
    if access["is_streamer"]:
        return ActivityUserType.STREAMER
    return ActivityUserType.STANDARD


def normalize_config(config: Optional[dict[str, Any]], guild_id: int) -> dict[str, Any]:
    config = config or {}
    return {
        "guild_id": guild_id,
        "title": config.get("title") or "Добро пожаловать!",
        "description": config.get("description") or "Привет, {user}! Добро пожаловать на {guild}.",
        "thumbnail_url": config.get("thumbnail_url"),
        "footer_text": config.get("footer_text"),
        "footer_icon_url": config.get("footer_icon_url"),
        "color": config.get("color") or 0x57F287,
        "is_enabled": config.get("is_enabled", 1) != 0,
        "rules_channel_id": config.get("rules_channel_id"),
        "roles_channel_id": config.get("roles_channel_id"),
    }


def get_db() -> DatabaseManager:
    if _db is None:
        raise HTTPException(status_code=503, detail="Database is not initialized")
    return _db


def get_role_purpose_service() -> ServerRolePurposeService:
    if _role_purpose_service is None:
        raise HTTPException(status_code=503, detail="Role purpose service is not initialized")
    return _role_purpose_service


if CLIENT_DIST.exists():
    app.mount("/assets", StaticFiles(directory=CLIENT_DIST / "assets"), name="activity-assets")


@app.get("/{path:path}")
async def serve_activity(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404)

    requested = CLIENT_DIST / path
    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(CLIENT_DIST / "index.html")

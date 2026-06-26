import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from application.services import ServerRolePurposeService
from application.schemas.server_role_purpose_schemas import ServerRolePurposeSchema
from core.domain.activity_user_type import ActivityUserType
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

from typing import Any

from fastapi import HTTPException

from activity.server.dependencies import get_db
from activity.server.schemas.voice_rooms import VoiceRoomUpdatePayload
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.audit_service import ActivityAuditService
from activity.server.services.discord_service import DiscordService
from activity.server.utils.voice_permissions import build_voice_lock_overwrites
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class VoiceRoomService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._audit_service = ActivityAuditService()
        self._discord = DiscordService()

    async def list_rooms(self, guild_id: int, access_token: str) -> list[dict[str, Any]]:
        logger.info("Listing Activity voice rooms guild_id=%s", guild_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(guild_id), "voice-rooms")
        if self._can_manage_all(access):
            rooms = await get_db().fetch_all(
                "SELECT * FROM voice_rooms WHERE guild_id = ? ORDER BY created_at DESC",
                (guild_id,),
            )
        else:
            rooms = await get_db().fetch_all(
                "SELECT * FROM voice_rooms WHERE guild_id = ? AND owner_id = ? ORDER BY created_at DESC",
                (guild_id, int(user["id"])),
            )
        results = []
        for room in rooms:
            channel = await self._discord.safe_bot_request("GET", f"/channels/{room['channel_id']}")
            results.append({**room, "discord": channel})
        return results

    async def update_room(self, channel_id: int, payload: VoiceRoomUpdatePayload, access_token: str) -> dict[str, Any]:
        logger.info("Updating Activity voice room guild_id=%s channel_id=%s", payload.guild_id, channel_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "voice-rooms")
        room = await self._get_authorized_room(payload.guild_id, channel_id, user, access)
        patch: dict[str, Any] = {}
        if payload.name is not None:
            patch["name"] = payload.name
        if payload.user_limit is not None:
            patch["user_limit"] = payload.user_limit
        if payload.locked is not None:
            channel = await self._discord.bot_request("GET", f"/channels/{channel_id}")
            patch["permission_overwrites"] = build_voice_lock_overwrites(channel, payload.guild_id, payload.locked)
        if patch:
            await self._discord.bot_request("PATCH", f"/channels/{channel_id}", json_body=patch)
        if payload.owner_id is not None:
            await get_db().execute("UPDATE voice_rooms SET owner_id = ? WHERE channel_id = ?", (payload.owner_id, channel_id))
        if payload.persistent is not None:
            await get_db().execute(
                "UPDATE voice_rooms SET is_persistent = ? WHERE channel_id = ?",
                (1 if payload.persistent else 0, channel_id),
            )
        await get_db().commit()
        await self._audit_service.log_action(
            guild_id=payload.guild_id,
            actor_id=int(user["id"]),
            actor_name=self._display_name(user),
            target_id=channel_id,
            target_name=room["name"],
            event_type="activity_voice_room_updated",
            details=f"Updated voice room {room['name']}.",
        )
        return {"channel_id": channel_id, "updated": True}

    async def delete_room(self, channel_id: int, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Deleting Activity voice room guild_id=%s channel_id=%s", guild_id, channel_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(guild_id), "voice-rooms")
        room = await self._get_authorized_room(guild_id, channel_id, user, access)
        await self._discord.safe_bot_request("DELETE", f"/channels/{channel_id}")
        await get_db().execute("DELETE FROM voice_rooms WHERE channel_id = ?", (channel_id,))
        await get_db().commit()
        await self._audit_service.log_action(
            guild_id=guild_id,
            actor_id=int(user["id"]),
            actor_name=self._display_name(user),
            target_id=channel_id,
            target_name=room["name"],
            event_type="activity_voice_room_deleted",
            details=f"Deleted voice room {room['name']}.",
        )
        return {"channel_id": channel_id, "deleted": True}

    async def _get_authorized_room(
        self,
        guild_id: int,
        channel_id: int,
        user: dict[str, Any],
        access: dict[str, Any],
    ) -> dict[str, Any]:
        room = await get_db().fetch_one(
            "SELECT * FROM voice_rooms WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        )
        if room is None:
            raise HTTPException(status_code=404, detail="Voice room not found")
        if self._can_manage_all(access) or int(room["owner_id"]) == int(user["id"]):
            return room
        logger.warning("Voice room access denied guild_id=%s channel_id=%s user_id=%s", guild_id, channel_id, user.get("id"))
        raise HTTPException(status_code=403, detail="Voice room owner permission is required")

    def _can_manage_all(self, access: dict[str, Any]) -> bool:
        return bool(access.get("is_admin")) or access.get("access_level") == "moderator"

    def _display_name(self, user: dict[str, Any]) -> str:
        return user.get("global_name") or user.get("username") or str(user.get("id"))

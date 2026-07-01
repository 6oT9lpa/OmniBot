from typing import Any, Optional

from fastapi import HTTPException

from activity.server.dependencies import get_db
from activity.server.schemas.voice_rooms import VoiceRoomUpdatePayload
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.audit_service import ActivityAuditService
from activity.server.services.discord_service import DiscordService
from activity.server.utils.voice_permissions import (
    build_member_admin_overwrites,
    build_member_connect_overwrites,
    build_voice_lock_overwrites,
    clear_member_overwrite,
)
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
                """
                SELECT * FROM voice_rooms
                WHERE guild_id = ? AND (owner_id = ? OR admin_id = ?)
                ORDER BY created_at DESC
                """,
                (guild_id, int(user["id"]), int(user["id"])),
            )

        results = []
        for room in rooms:
            channel = await self._discord.safe_bot_request("GET", f"/channels/{room['channel_id']}")
            voice_member_ids = await self._list_voice_member_ids(guild_id, int(room["channel_id"]))
            results.append(self._serialize_room(room, channel, voice_member_ids))
        logger.info("Activity voice rooms listed guild_id=%s count=%s", guild_id, len(results))
        return results

    async def update_room(self, channel_id: int, payload: VoiceRoomUpdatePayload, access_token: str) -> dict[str, Any]:
        logger.info("Updating Activity voice room guild_id=%s channel_id=%s", payload.guild_id, channel_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "voice-rooms")
        room = await self._get_authorized_room(payload.guild_id, channel_id, user, access)
        patch: dict[str, Any] = {}
        channel: Optional[dict[str, Any]] = None
        admin_cleared_by_ban = False
        final_admin_id: int | None | str = "unchanged"

        if payload.name is not None:
            patch["name"] = payload.name
        if payload.user_limit is not None:
            patch["user_limit"] = payload.user_limit
        if payload.rtc_region is not None:
            patch["rtc_region"] = payload.rtc_region or None
        if payload.locked is not None:
            channel = channel or await self._discord.bot_request("GET", f"/channels/{channel_id}")
            patch["permission_overwrites"] = build_voice_lock_overwrites(channel, payload.guild_id, payload.locked)
            channel["permission_overwrites"] = patch["permission_overwrites"]
        if payload.invite_user_id is not None:
            channel = channel or await self._discord.bot_request("GET", f"/channels/{channel_id}")
            patch["permission_overwrites"] = build_member_connect_overwrites(channel, payload.invite_user_id, allowed=True)
            channel["permission_overwrites"] = patch["permission_overwrites"]
        if payload.ban_user_id is not None:
            await self._validate_member_removal(payload.ban_user_id, channel_id, room, user)
            channel = channel or await self._discord.bot_request("GET", f"/channels/{channel_id}")
            if room.get("admin_id") and int(room["admin_id"]) == int(payload.ban_user_id):
                channel["permission_overwrites"] = clear_member_overwrite(channel, payload.ban_user_id)
                admin_cleared_by_ban = True
                final_admin_id = None
                logger.info("Voice admin cleared because admin was banned channel_id=%s admin_id=%s", channel_id, payload.ban_user_id)
            patch["permission_overwrites"] = build_member_connect_overwrites(channel, payload.ban_user_id, allowed=False)
            channel["permission_overwrites"] = patch["permission_overwrites"]

        admin_changed, requested_admin_id = await self._apply_admin_payload(channel_id, payload, room, user, access, patch, channel)
        admin_changed = admin_changed or admin_cleared_by_ban
        if requested_admin_id != "unchanged":
            final_admin_id = requested_admin_id

        if patch:
            await self._discord.bot_request("PATCH", f"/channels/{channel_id}", json_body=patch)
        if payload.kick_user_id is not None:
            await self._validate_member_removal(payload.kick_user_id, channel_id, room, user)
            await self._discord.bot_request(
                "PATCH",
                f"/guilds/{payload.guild_id}/members/{payload.kick_user_id}",
                json_body={"channel_id": None},
            )
        if payload.ban_user_id is not None:
            await self._discord.bot_request(
                "PATCH",
                f"/guilds/{payload.guild_id}/members/{payload.ban_user_id}",
                json_body={"channel_id": None},
            )
        if payload.owner_id is not None:
            logger.info("Ignored immutable owner update request channel_id=%s requested_owner_id=%s", channel_id, payload.owner_id)
        db_changed = False
        if final_admin_id != "unchanged":
            await get_db().execute("UPDATE voice_rooms SET admin_id = ? WHERE channel_id = ?", (final_admin_id, channel_id))
            db_changed = True
        if payload.persistent is not None:
            await get_db().execute(
                "UPDATE voice_rooms SET is_persistent = ? WHERE channel_id = ?",
                (1 if payload.persistent else 0, channel_id),
            )
            db_changed = True
        if db_changed:
            await get_db().commit()
        await self._audit_service.log_action(
            guild_id=payload.guild_id,
            actor_id=int(user["id"]),
            actor_name=self._display_name(user),
            target_id=channel_id,
            target_name=room["name"],
            event_type="activity_voice_room_updated",
            details=f"Updated voice room {room['name']}. admin_changed={admin_changed}",
        )
        logger.info("Activity voice room updated guild_id=%s channel_id=%s admin_changed=%s", payload.guild_id, channel_id, admin_changed)
        return {"channel_id": channel_id, "updated": True}

    async def delete_room(self, channel_id: int, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Deleting Activity voice room guild_id=%s channel_id=%s", guild_id, channel_id)
        user, access = await self._access_service.ensure_module_access(access_token, str(guild_id), "voice-rooms")
        room = await self._get_authorized_room(guild_id, channel_id, user, access)
        await self._discord.safe_bot_request("DELETE", f"/channels/{channel_id}")
        await get_db().execute("DELETE FROM voice_room_members WHERE channel_id = ?", (channel_id,))
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
        logger.info("Activity voice room deleted guild_id=%s channel_id=%s", guild_id, channel_id)
        return {"channel_id": channel_id, "deleted": True}

    async def _apply_admin_payload(
        self,
        channel_id: int,
        payload: VoiceRoomUpdatePayload,
        room: dict[str, Any],
        user: dict[str, Any],
        access: dict[str, Any],
        patch: dict[str, Any],
        channel: Optional[dict[str, Any]],
    ) -> tuple[bool, int | None | str]:
        requested_admin_id = self._resolve_requested_admin_id(payload, room, user)
        if requested_admin_id == "unchanged":
            return False, "unchanged"

        if not self._can_assign_admin(room, user, access, payload):
            logger.warning("Voice admin update denied channel_id=%s user_id=%s", channel_id, user.get("id"))
            raise HTTPException(status_code=403, detail="Voice room owner permission is required for admin assignment")

        if requested_admin_id is not None and requested_admin_id == int(room["owner_id"]):
            raise HTTPException(status_code=400, detail="Owner cannot become admin")
        if requested_admin_id is not None and requested_admin_id not in await self._load_voice_member_ids(channel_id):
            logger.warning(
                "Voice admin update rejected because target is not in room channel_id=%s target_id=%s",
                channel_id,
                requested_admin_id,
            )
            raise HTTPException(status_code=400, detail="Admin must be a current voice room member")

        channel = channel or await self._discord.bot_request("GET", f"/channels/{channel_id}")
        current_admin_id = int(room["admin_id"]) if room.get("admin_id") else None
        if current_admin_id:
            patch["permission_overwrites"] = clear_member_overwrite(channel, current_admin_id)
            channel["permission_overwrites"] = patch["permission_overwrites"]

        if requested_admin_id is not None:
            patch["permission_overwrites"] = build_member_admin_overwrites(channel, requested_admin_id)
            channel["permission_overwrites"] = patch["permission_overwrites"]

        logger.info("Voice admin payload applied channel_id=%s old_admin_id=%s new_admin_id=%s", channel_id, current_admin_id, requested_admin_id)
        return True, requested_admin_id

    def _resolve_requested_admin_id(
        self,
        payload: VoiceRoomUpdatePayload,
        room: dict[str, Any],
        user: dict[str, Any],
    ) -> int | None | str:
        if payload.claim_admin:
            if room.get("admin_id"):
                raise HTTPException(status_code=409, detail="Admin rights are already taken")
            if int(room["owner_id"]) == int(user["id"]):
                raise HTTPException(status_code=400, detail="Owner cannot become admin")
            return int(user["id"])
        if payload.release_admin:
            admin_id = int(room["admin_id"]) if room.get("admin_id") else None
            if admin_id != int(user["id"]):
                raise HTTPException(status_code=403, detail="Only current admin can release admin rights")
            return None
        if "admin_id" in payload.model_fields_set:
            return payload.admin_id
        return "unchanged"

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
        admin_id = int(room["admin_id"]) if room.get("admin_id") else None
        if self._can_manage_all(access) or int(room["owner_id"]) == int(user["id"]) or admin_id == int(user["id"]):
            return room
        logger.warning("Voice room access denied guild_id=%s channel_id=%s user_id=%s", guild_id, channel_id, user.get("id"))
        raise HTTPException(status_code=403, detail="Voice room owner or admin permission is required")

    def _can_assign_admin(
        self,
        room: dict[str, Any],
        user: dict[str, Any],
        access: dict[str, Any],
        payload: VoiceRoomUpdatePayload,
    ) -> bool:
        if payload.claim_admin or payload.release_admin:
            return True
        return int(room["owner_id"]) == int(user["id"])

    async def _validate_member_removal(
        self,
        target_id: int,
        channel_id: int,
        room: dict[str, Any],
        user: dict[str, Any],
    ) -> None:
        if target_id == int(user["id"]):
            raise HTTPException(status_code=400, detail="You cannot kick or ban yourself")
        if target_id == int(room["owner_id"]):
            raise HTTPException(status_code=400, detail="Owner cannot be kicked or banned from the room")
        if target_id not in await self._load_voice_member_ids(channel_id):
            raise HTTPException(status_code=400, detail="Target must be a current voice room member")

    def _can_manage_all(self, access: dict[str, Any]) -> bool:
        return bool(access.get("is_admin")) or access.get("access_level") == "moderator"

    def _display_name(self, user: dict[str, Any]) -> str:
        return user.get("global_name") or user.get("username") or str(user.get("id"))

    async def _list_voice_member_ids(self, guild_id: int, channel_id: int) -> list[str]:
        member_ids = [str(member_id) for member_id in sorted(await self._load_voice_member_ids(channel_id))]
        logger.info("Voice room members resolved guild_id=%s channel_id=%s count=%s", guild_id, channel_id, len(member_ids))
        return member_ids

    async def _load_voice_member_ids(self, channel_id: int) -> set[int]:
        rows = await get_db().fetch_all(
            "SELECT user_id FROM voice_room_members WHERE channel_id = ?",
            (channel_id,),
        )
        return {int(row["user_id"]) for row in rows}

    def _serialize_room(
        self,
        room: dict[str, Any],
        channel: dict[str, Any] | None,
        voice_member_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        logger.info("Serializing Activity voice room channel_id=%s", room.get("channel_id"))
        return {
            **room,
            "channel_id": str(room["channel_id"]),
            "guild_id": str(room["guild_id"]),
            "owner_id": str(room["owner_id"]),
            "admin_id": str(room["admin_id"]) if room.get("admin_id") else None,
            "is_persistent": bool(room.get("is_persistent")),
            "voice_member_ids": voice_member_ids or [],
            "discord": channel,
        }

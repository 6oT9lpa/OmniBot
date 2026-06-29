from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, Tuple

import disnake

from application.dto.voice_dto import VoiceRoomDTO
from application.schemas.voice_schemas import (
    VoiceInviteSchema,
    VoiceLimitSchema,
    VoiceRenameSchema,
)
from core.interfaces.repositories import VoiceRepositoryInterface
from core.interfaces.services import VoiceServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)

_MSK = timezone(timedelta(hours=3))


class VoiceService(VoiceServiceInterface):
    def __init__(self, repo: VoiceRepositoryInterface) -> None:
        self._repo = repo
        self._delete_tasks: Dict[int, asyncio.Task] = {}
        self._creating: Set[Tuple[int, int]] = set()

    async def create(
        self,
        member: disnake.Member,
        trigger_channel: disnake.VoiceChannel,
    ) -> Optional[disnake.VoiceChannel]:
        key = (member.id, member.guild.id)
        logger.info("Voice room create requested: guild_id=%s user_id=%s", member.guild.id, member.id)
        if key in self._creating:
            logger.debug("Already creating room for user_id=%s", member.id)
            return None

        existing = await self._repo.get_by_owner(member.id, member.guild.id)
        if existing:
            channel = member.guild.get_channel(existing["channel_id"])
            if channel:
                try:
                    await member.move_to(channel)
                    logger.debug("Redirected user_id=%s to existing room", member.id)
                except Exception as exc:
                    logger.warning("Failed to redirect user_id=%s: %s", member.id, exc)
                return None
            await self._repo.delete(existing["channel_id"])
            logger.warning("Stale voice room removed: channel_id=%s", existing["channel_id"])

        self._creating.add(key)
        try:
            return await self._create_room(member, trigger_channel)
        finally:
            self._creating.discard(key)

    async def delete(self, channel: disnake.VoiceChannel) -> None:
        logger.info("Voice room delete requested: channel_id=%s", channel.id)
        try:
            await self._repo.delete(channel.id)
            await channel.delete()
            logger.info("Voice room deleted: channel_id=%s name=%s", channel.id, channel.name)
        except Exception as exc:
            logger.error("Failed to delete voice room channel_id=%s: %s", channel.id, exc)
            raise

    async def schedule_delete(self, channel: disnake.VoiceChannel, delay: float = 10.0) -> None:
        self._cancel_task(channel.id)

        async def _delayed_delete() -> None:
            await asyncio.sleep(delay)
            if not channel.members:
                await self.delete(channel)
            self._delete_tasks.pop(channel.id, None)

        self._delete_tasks[channel.id] = asyncio.create_task(_delayed_delete())
        logger.debug("Scheduled delete for channel_id=%s in %.0fs", channel.id, delay)

    async def cancel_delete(self, channel_id: int) -> None:
        self._cancel_task(channel_id)

    async def handle_admin_leave(
        self,
        channel: disnake.VoiceChannel,
        old_admin: disnake.Member,
    ) -> None:
        # Admin is intentionally temporary; owner_id remains the creator forever.
        room = await self._repo.get(channel.id)
        admin_id = int(room["admin_id"]) if room and room.get("admin_id") else None
        if not room or admin_id != old_admin.id:
            logger.debug("Skip admin leave handling channel_id=%s user_id=%s", channel.id, old_admin.id)
            return

        try:
            await self._clear_admin(channel, old_admin)
            logger.info("Temporary voice admin cleared on leave: channel_id=%s admin_id=%s", channel.id, old_admin.id)
        except Exception as exc:
            logger.error("Failed to clear voice admin on leave channel_id=%s: %s", channel.id, exc)
            raise

    async def rename(
        self,
        channel: disnake.VoiceChannel,
        new_name: str,
        user: disnake.Member,
    ) -> None:
        logger.info("Voice room rename requested: channel_id=%s user_id=%s", channel.id, user.id)
        if not await self._can_control(user, channel):
            logger.warning("User %s lacks voice control for rename in %s", user.id, channel.id)
            raise PermissionError("Not enough rights to rename the room")

        schema = VoiceRenameSchema(name=new_name)
        try:
            await channel.edit(name=schema.name)
            logger.debug("Voice room renamed: channel_id=%s new_name=%s user_id=%s", channel.id, schema.name, user.id)
        except Exception as exc:
            logger.error("Failed to rename channel_id=%s: %s", channel.id, exc)
            raise

    async def set_limit(
        self,
        channel: disnake.VoiceChannel,
        limit: int,
        user: disnake.Member,
    ) -> None:
        logger.info("Voice room limit requested: channel_id=%s user_id=%s limit=%s", channel.id, user.id, limit)
        if not await self._can_control(user, channel):
            logger.warning("User %s lacks voice control for limit in %s", user.id, channel.id)
            raise PermissionError("Not enough rights to set the room limit")

        schema = VoiceLimitSchema(limit=limit)
        try:
            await channel.edit(user_limit=schema.limit)
            logger.debug("Voice limit set: channel_id=%s limit=%s user_id=%s", channel.id, schema.limit, user.id)
        except Exception as exc:
            logger.error("Failed to set limit channel_id=%s: %s", channel.id, exc)
            raise

    async def lock(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        logger.info("Voice room lock requested: channel_id=%s user_id=%s", channel.id, user.id)
        await self._set_everyone_connect(channel, user, allow=False)

    async def unlock(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        logger.info("Voice room unlock requested: channel_id=%s user_id=%s", channel.id, user.id)
        await self._set_everyone_connect(channel, user, allow=True)

    async def transfer(
        self,
        channel: disnake.VoiceChannel,
        new_owner: disnake.Member,
        user: disnake.Member,
    ) -> None:
        await self.assign_admin(channel, new_owner, user)

    async def claim_admin(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        logger.info("Voice admin claim requested: channel_id=%s user_id=%s", channel.id, user.id)
        room = await self._require_room(channel)
        if int(room["owner_id"]) == user.id:
            logger.warning("Owner %s attempted to claim admin in channel_id=%s", user.id, channel.id)
            raise PermissionError("Owner cannot become admin")
        admin_id = int(room["admin_id"]) if room.get("admin_id") else None
        if admin_id and admin_id != user.id:
            logger.warning("User %s attempted to claim occupied admin channel_id=%s", user.id, channel.id)
            raise PermissionError("Admin rights are already taken")

        await self._grant_admin(channel, user)
        logger.info("Temporary voice admin claimed: channel_id=%s admin_id=%s", channel.id, user.id)

    async def release_admin(self, channel: disnake.VoiceChannel, user: disnake.Member) -> None:
        logger.info("Voice admin release requested: channel_id=%s user_id=%s", channel.id, user.id)
        room = await self._require_room(channel)
        admin_id = int(room["admin_id"]) if room.get("admin_id") else None
        if admin_id != user.id:
            logger.warning("User %s attempted to release admin in channel_id=%s", user.id, channel.id)
            raise PermissionError("Only current admin can release admin rights")

        await self._clear_admin(channel, user)
        logger.info("Temporary voice admin released: channel_id=%s admin_id=%s", channel.id, user.id)

    async def assign_admin(
        self,
        channel: disnake.VoiceChannel,
        new_admin: Optional[disnake.Member],
        user: disnake.Member,
    ) -> None:
        logger.info(
            "Voice admin assignment requested: channel_id=%s user_id=%s target_id=%s",
            channel.id,
            user.id,
            getattr(new_admin, "id", None),
        )
        room = await self._require_room(channel)
        if int(room["owner_id"]) != user.id:
            logger.warning("User %s attempted owner-only admin assignment channel_id=%s", user.id, channel.id)
            raise PermissionError("Only owner can assign admin rights")
        if new_admin and new_admin.id == int(room["owner_id"]):
            logger.warning("Owner %s cannot be assigned as admin channel_id=%s", new_admin.id, channel.id)
            raise PermissionError("Owner cannot become admin")
        if new_admin and new_admin.bot:
            logger.warning("Bot %s cannot be assigned as admin channel_id=%s", new_admin.id, channel.id)
            raise PermissionError("Bot cannot become admin")

        current_admin = self._member_from_room(channel, room.get("admin_id"))
        if current_admin:
            await self._clear_admin(channel, current_admin)
        elif room.get("admin_id"):
            await self._repo.update_admin(channel.id, None)

        if new_admin:
            await self._grant_admin(channel, new_admin)
            logger.info("Temporary voice admin assigned: channel_id=%s owner_id=%s admin_id=%s", channel.id, user.id, new_admin.id)
        else:
            logger.info("Temporary voice admin cleared by owner: channel_id=%s owner_id=%s", channel.id, user.id)

    async def track_member_join(self, channel: disnake.VoiceChannel, member: disnake.Member) -> None:
        room = await self._repo.get(channel.id)
        if not room:
            logger.debug("Skip voice member join tracking because room is missing channel_id=%s user_id=%s", channel.id, member.id)
            return
        await self._repo.add_member(channel.id, member.guild.id, member.id)
        logger.debug("Voice member join tracked: guild_id=%s channel_id=%s user_id=%s", member.guild.id, channel.id, member.id)

    async def track_member_leave(self, channel: disnake.VoiceChannel, member: disnake.Member) -> None:
        room = await self._repo.get(channel.id)
        if not room:
            logger.debug("Skip voice member leave tracking because room is missing channel_id=%s user_id=%s", channel.id, member.id)
            return
        await self._repo.remove_member(channel.id, member.id)
        logger.debug("Voice member leave tracked: guild_id=%s channel_id=%s user_id=%s", member.guild.id, channel.id, member.id)

    async def invite(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
    ) -> None:
        logger.info("Voice invite requested: channel_id=%s user_id=%s target_id=%s", channel.id, user.id, target.id)
        if not await self._can_control(user, channel):
            logger.warning("User %s lacks voice control for invite in %s", user.id, channel.id)
            raise PermissionError("Not enough rights to invite users")

        schema = VoiceInviteSchema(user_id=target.id)
        try:
            await channel.set_permissions(target, connect=True)
            await channel.send(f"{target.mention}, вас пригласил {user.mention}!")
            await self._try_dm_invite(target, user, channel)
            logger.debug("Invited user_id=%s to channel_id=%s by user_id=%s", schema.user_id, channel.id, user.id)
        except Exception as exc:
            logger.error("Failed to invite target_id=%s channel_id=%s: %s", target.id, channel.id, exc)
            raise

    async def kick(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
    ) -> None:
        await self._remove_from_room(channel, target, user, ban=False)

    async def ban(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
    ) -> None:
        await self._remove_from_room(channel, target, user, ban=True)

    async def set_trigger(self, guild_id: int, channel_id: int) -> None:
        await self._repo.set_config(f"trigger_{guild_id}", str(channel_id))
        logger.info("Trigger set for guild %s: channel %s", guild_id, channel_id)

    async def get_trigger(self, guild_id: int) -> Optional[int]:
        value = await self._repo.get_config(f"trigger_{guild_id}")
        logger.debug("Trigger fetched for guild_id=%s exists=%s", guild_id, bool(value))
        return int(value) if value else None

    async def remove_trigger(self, guild_id: int) -> None:
        await self._repo.set_config(f"trigger_{guild_id}", "")
        logger.info("Trigger removed for guild %s", guild_id)

    async def _create_room(
        self,
        member: disnake.Member,
        trigger_channel: disnake.VoiceChannel,
    ) -> Optional[disnake.VoiceChannel]:
        guild = member.guild
        room_name = f"🔊 {member.display_name}"

        try:
            channel = await guild.create_voice_channel(
                name=room_name,
                category=trigger_channel.category,
                overwrites={
                    guild.default_role: disnake.PermissionOverwrite(connect=False),
                    member: disnake.PermissionOverwrite(
                        connect=True,
                        manage_channels=True,
                        manage_permissions=True,
                        move_members=True,
                    ),
                },
            )
            await member.move_to(channel)
            await self._repo.create(
                VoiceRoomDTO(
                    channel_id=channel.id,
                    guild_id=guild.id,
                    owner_id=member.id,
                    admin_id=None,
                    name=room_name,
                    created_at=datetime.now(_MSK),
                )
            )
            await self._repo.add_member(channel.id, guild.id, member.id)
            logger.info("Voice room created: channel_id=%s name=%s owner=%s", channel.id, room_name, member.id)
            return channel
        except Exception as exc:
            logger.error("Failed to create voice room for user_id=%s: %s", member.id, exc)
            raise

    async def _grant_admin(self, channel: disnake.VoiceChannel, admin: disnake.Member) -> None:
        await channel.set_permissions(
            admin,
            connect=True,
            manage_channels=True,
            manage_permissions=True,
            move_members=True,
        )
        await self._repo.update_admin(channel.id, admin.id)
        logger.debug("Admin permissions granted: channel_id=%s admin_id=%s", channel.id, admin.id)

    async def _clear_admin(self, channel: disnake.VoiceChannel, admin: disnake.Member) -> None:
        room = await self._require_room(channel)
        if int(room["owner_id"]) != admin.id:
            await channel.set_permissions(admin, overwrite=None)
        await self._repo.update_admin(channel.id, None)
        logger.debug("Admin permissions cleared: channel_id=%s admin_id=%s", channel.id, admin.id)

    async def _set_everyone_connect(
        self,
        channel: disnake.VoiceChannel,
        user: disnake.Member,
        *,
        allow: bool,
    ) -> None:
        if not await self._can_control(user, channel):
            logger.warning("User %s lacks voice control for lock/unlock in %s", user.id, channel.id)
            raise PermissionError("Not enough rights to change room access")

        try:
            await channel.set_permissions(user.guild.default_role, connect=allow)
            logger.debug("Channel connect=%s channel_id=%s user_id=%s", allow, channel.id, user.id)
        except Exception as exc:
            logger.error("Failed to set connect permission channel_id=%s: %s", channel.id, exc)
            raise

    async def _remove_from_room(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
        *,
        ban: bool,
    ) -> None:
        if not await self._can_control(user, channel):
            logger.warning("User %s lacks voice control for kick/ban in %s", user.id, channel.id)
            raise PermissionError("Not enough rights to remove users")

        try:
            await channel.set_permissions(target, connect=False)
            if target.voice and target.voice.channel == channel:
                await target.move_to(None)
            action = "banned" if ban else "kicked"
            logger.debug("User %s from channel_id=%s target_id=%s by user_id=%s", action, channel.id, target.id, user.id)
        except Exception as exc:
            logger.error("Failed to remove target_id=%s from channel_id=%s: %s", target.id, channel.id, exc)
            raise

    async def _try_dm_invite(
        self,
        target: disnake.Member,
        inviter: disnake.Member,
        channel: disnake.VoiceChannel,
    ) -> None:
        try:
            await target.send(
                f"**{inviter.display_name}** приглашает вас в **{channel.name}**!\n{channel.mention}"
            )
        except disnake.Forbidden:
            logger.debug("DM closed for target_id=%s", target.id)
        except Exception as exc:
            logger.debug("Failed to DM invite target_id=%s: %s", target.id, exc)

    async def _require_room(self, channel: disnake.VoiceChannel) -> dict:
        room = await self._repo.get(channel.id)
        if not room:
            logger.warning("Voice room metadata missing: channel_id=%s", channel.id)
            raise PermissionError("Voice room metadata was not found")
        return room

    def _member_from_room(self, channel: disnake.VoiceChannel, member_id: Optional[int]) -> Optional[disnake.Member]:
        if not member_id:
            return None
        return channel.guild.get_member(int(member_id))

    async def _can_control(self, user: disnake.Member, channel: disnake.VoiceChannel) -> bool:
        room = await self._repo.get(channel.id)
        if not room:
            logger.debug("Control denied because room metadata is missing channel_id=%s user_id=%s", channel.id, user.id)
            return False
        admin_id = int(room["admin_id"]) if room.get("admin_id") else None
        if int(room["owner_id"]) == user.id or admin_id == user.id:
            return True
        return self._has_manage_permissions(user, channel)

    def _cancel_task(self, channel_id: int) -> None:
        task = self._delete_tasks.pop(channel_id, None)
        if task:
            task.cancel()
            logger.debug("Delete task cancelled for channel_id=%s", channel_id)

    @staticmethod
    def _has_manage_permissions(user: disnake.Member, channel: disnake.VoiceChannel) -> bool:
        return channel.permissions_for(user).manage_permissions

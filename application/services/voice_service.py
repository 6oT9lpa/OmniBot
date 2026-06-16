from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, Tuple

import disnake

from application.dto.voice_dto import VoiceRoomDTO
from application.schemas.voice_schemas import (
    VoiceInviteSchema,
    VoiceLimitSchema,
    VoiceRenameSchema,
    VoiceRoomCreateSchema,
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
        """Создать голосовую комнату для участника."""
        key = (member.id, member.guild.id)
        if key in self._creating:
            logger.debug("Already creating room for user_id=%s", member.id)
            return None

        existing = await self._repo.get_by_owner(member.id, member.guild.id)
        if existing:
            ch = member.guild.get_channel(existing["channel_id"])
            if ch:
                try:
                    await member.move_to(ch)
                    logger.debug("Redirected user_id=%s to existing room", member.id)
                except Exception as exc:
                    logger.warning("Failed to redirect user_id=%s: %s", member.id, exc)
                return None
            else:
                await self._repo.delete(existing["channel_id"])
                logger.warning("Stale voice room removed: channel_id=%s", existing["channel_id"])

        self._creating.add(key)
        try:
            return await self._create_room(member, trigger_channel)
        finally:
            self._creating.discard(key)

    async def delete(self, channel: disnake.VoiceChannel) -> None:
        """Удалить голосовую комнату."""
        try:
            await self._repo.delete(channel.id)
            await channel.delete()
            logger.info("Voice room deleted: channel_id=%s name=%s", channel.id, channel.name)
        except Exception as exc:
            logger.error("Failed to delete voice room channel_id=%s: %s", channel.id, exc)
            raise

    async def schedule_delete(self, channel: disnake.VoiceChannel, delay: float = 30.0) -> None:
        """Запланировать удаление пустой комнаты через `delay` секунд."""
        self._cancel_task(channel.id)

        async def _delayed_delete() -> None:
            await asyncio.sleep(delay)
            if not channel.members:
                await self.delete(channel)
            self._delete_tasks.pop(channel.id, None)

        self._delete_tasks[channel.id] = asyncio.create_task(_delayed_delete())
        logger.debug("Scheduled delete for channel_id=%s in %.0fs", channel.id, delay)

    async def cancel_delete(self, channel_id: int) -> None:
        """Отменить запланированное удаление."""
        self._cancel_task(channel_id)

    async def handle_owner_leave(
        self,
        channel: disnake.VoiceChannel,
        old_owner: disnake.Member,
    ) -> None:
        """Передать владение случайному участнику при уходе владельца."""
        candidates = [m for m in channel.members if not m.bot and m.id != old_owner.id]
        if not candidates:
            return

        new_owner = random.choice(candidates)
        try:
            await self._transfer_ownership(channel, old_owner, new_owner)
            logger.info(
                "Ownership auto-transferred: channel_id=%s new_owner=%s",
                channel.id, new_owner.id,
            )
        except Exception as exc:
            logger.error(
                "Failed to auto-transfer ownership channel_id=%s: %s",
                channel.id, exc,
            )
            raise

    async def rename(
        self,
        channel: disnake.VoiceChannel,
        new_name: str,
        user: disnake.Member,
    ) -> None:
        """Переименовать комнату."""
        if not self._has_manage(user, channel):
            logger.warning("User %s lacks manage_channels for rename in %s", user.id, channel.id)
            raise PermissionError("Недостаточно прав для переименования канала")

        schema = VoiceRenameSchema(name=new_name)
        try:
            await channel.edit(name=schema.name)
            logger.debug(
                "Voice room renamed: channel_id=%s new_name=%s user_id=%s",
                channel.id, schema.name, user.id,
            )
        except Exception as exc:
            logger.error("Failed to rename channel_id=%s: %s", channel.id, exc)
            raise

    async def set_limit(
        self,
        channel: disnake.VoiceChannel,
        limit: int,
        user: disnake.Member,
    ) -> None:
        """Установить лимит участников."""
        if not self._has_manage(user, channel):
            logger.warning("User %s lacks manage_channels for limit in %s", user.id, channel.id)
            raise PermissionError("Недостаточно прав для установки лимита")

        schema = VoiceLimitSchema(limit=limit)
        try:
            await channel.edit(user_limit=schema.limit)
            logger.debug(
                "Voice limit set: channel_id=%s limit=%s user_id=%s",
                channel.id, schema.limit, user.id,
            )
        except Exception as exc:
            logger.error("Failed to set limit channel_id=%s: %s", channel.id, exc)
            raise

    async def lock(
        self,
        channel: disnake.VoiceChannel,
        user: disnake.Member,
    ) -> None:
        """Закрыть комнату (запретить вход @everyone)."""
        await self._set_everyone_connect(channel, user, allow=False)

    async def unlock(
        self,
        channel: disnake.VoiceChannel,
        user: disnake.Member,
    ) -> None:
        """Открыть комнату."""
        await self._set_everyone_connect(channel, user, allow=True)

    async def transfer(
        self,
        channel: disnake.VoiceChannel,
        new_owner: disnake.Member,
        user: disnake.Member,
    ) -> None:
        """Передать владение другому участнику."""
        if not self._has_manage_permissions(user, channel):
            logger.warning("User %s lacks manage_permissions for transfer in %s", user.id, channel.id)
            raise PermissionError("Недостаточно прав для передачи владения")

        try:
            await self._transfer_ownership(channel, user, new_owner)
            logger.info(
                "Ownership transferred: channel_id=%s from=%s to=%s",
                channel.id, user.id, new_owner.id,
            )
        except Exception as exc:
            logger.error("Failed to transfer ownership channel_id=%s: %s", channel.id, exc)
            raise

    async def invite(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
    ) -> None:
        """Пригласить участника в комнату."""
        if not self._has_manage_permissions(user, channel):
            logger.warning("User %s lacks manage_permissions for invite in %s", user.id, channel.id)
            raise PermissionError("Недостаточно прав для приглашения")

        schema = VoiceInviteSchema(user_id=target.id)
        try:
            await channel.set_permissions(target, connect=True)
            await channel.send(f"📩 {target.mention}, вас пригласил {user.mention}!")
            await self._try_dm_invite(target, user, channel)
            logger.debug(
                "Invited user_id=%s to channel_id=%s by user_id=%s",
                schema.user_id, channel.id, user.id,
            )
        except Exception as exc:
            logger.error("Failed to invite target_id=%s channel_id=%s: %s", target.id, channel.id, exc)
            raise

    async def kick(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
    ) -> None:
        """Выгнать участника из комнаты."""
        await self._remove_from_room(channel, target, user, ban=False)

    async def ban(
        self,
        channel: disnake.VoiceChannel,
        target: disnake.Member,
        user: disnake.Member,
    ) -> None:
        """Забанить участника в комнате."""
        await self._remove_from_room(channel, target, user, ban=True)

    async def set_trigger(self, guild_id: int, channel_id: int) -> None:
        """Установить триггерный канал."""
        await self._repo.set_config(f"trigger_{guild_id}", str(channel_id))
        logger.info("Trigger set for guild %s: channel %s", guild_id, channel_id)

    async def get_trigger(self, guild_id: int) -> Optional[int]:
        """Получить триггерный канал."""
        val = await self._repo.get_config(f"trigger_{guild_id}")
        return int(val) if val else None

    async def remove_trigger(self, guild_id: int) -> None:
        """Удалить триггерный канал."""
        await self._repo.set_config(f"trigger_{guild_id}", "")
        logger.info("Trigger removed for guild %s", guild_id)

    async def _create_room(
        self,
        member: disnake.Member,
        trigger_channel: disnake.VoiceChannel,
    ) -> Optional[disnake.VoiceChannel]:
        """Создать новую голосовую комнату на Discord и сохранить в БД."""
        guild = member.guild
        schema = VoiceRoomCreateSchema(
            channel_id=0,
            guild_id=guild.id,
            owner_id=member.id,
            name=f"🔊 {member.display_name}",
        )
        try:
            channel = await guild.create_voice_channel(
                name=schema.name,
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
                    name=schema.name,
                    created_at=datetime.now(_MSK),
                )
            )
            logger.info(
                "Voice room created: channel_id=%s name=%s owner=%s",
                channel.id, schema.name, member.id,
            )
            return channel
        except Exception as exc:
            logger.error("Failed to create voice room for user_id=%s: %s", member.id, exc)
            raise

    async def _transfer_ownership(
        self,
        channel: disnake.VoiceChannel,
        old_owner: disnake.Member,
        new_owner: disnake.Member,
    ) -> None:
        """Внутренняя передача прав владения комнатой."""
        await channel.set_permissions(old_owner, overwrite=None)
        await channel.set_permissions(
            new_owner,
            connect=True,
            manage_channels=True,
            manage_permissions=True,
            move_members=True,
        )
        await self._repo.update_owner(channel.id, new_owner.id)
        await channel.edit(name=f"🔊 {new_owner.display_name}")

    async def _set_everyone_connect(
        self,
        channel: disnake.VoiceChannel,
        user: disnake.Member,
        *,
        allow: bool,
    ) -> None:
        """Установить/снять ограничение connect для @everyone."""
        if not self._has_manage_permissions(user, channel):
            logger.warning("User %s lacks manage_permissions for lock/unlock in %s", user.id, channel.id)
            raise PermissionError("Недостаточно прав для изменения доступа")

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
        """Убрать участника из комнаты (kick или ban)."""
        if not self._has_manage_permissions(user, channel):
            logger.warning("User %s lacks manage_permissions for kick/ban in %s", user.id, channel.id)
            raise PermissionError("Недостаточно прав для удаления участника")

        try:
            await channel.set_permissions(target, connect=False)
            if target.voice and target.voice.channel == channel:
                await target.move_to(None)
            action = "banned" if ban else "kicked"
            logger.debug(
                "User %s from channel_id=%s target_id=%s by user_id=%s",
                action, channel.id, target.id, user.id,
            )
        except Exception as exc:
            logger.error("Failed to remove target_id=%s from channel_id=%s: %s", target.id, channel.id, exc)
            raise

    async def _try_dm_invite(
        self,
        target: disnake.Member,
        inviter: disnake.Member,
        channel: disnake.VoiceChannel,
    ) -> None:
        """Отправить DM приглашённому (ошибки игнорируются)."""
        try:
            await target.send(
                f"📩 **{inviter.display_name}** приглашает вас в "
                f"**{channel.name}**!\n{channel.mention}"
            )
        except disnake.Forbidden:
            logger.debug("DM closed for target_id=%s", target.id)
        except Exception as exc:
            logger.debug("Failed to DM invite target_id=%s: %s", target.id, exc)

    def _cancel_task(self, channel_id: int) -> None:
        """Отменить задачу удаления, если она существует."""
        task = self._delete_tasks.pop(channel_id, None)
        if task:
            task.cancel()
            logger.debug("Delete task cancelled for channel_id=%s", channel_id)

    @staticmethod
    def _has_manage(user: disnake.Member, channel: disnake.VoiceChannel) -> bool:
        return channel.permissions_for(user).manage_channels

    @staticmethod
    def _has_manage_permissions(user: disnake.Member, channel: disnake.VoiceChannel) -> bool:
        return channel.permissions_for(user).manage_permissions
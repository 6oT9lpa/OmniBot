from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union

import disnake

from application.dto.moderation_dto import PunishmentDTO
from core.domain.value_objects import PunishmentType
from core.interfaces.repositories import PunishmentRepositoryInterface
from core.interfaces.services import LoggingServiceInterface, ModerationHistoryServiceInterface, ModeratorServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ModeratorService(ModeratorServiceInterface):
    def __init__(
        self,
        punishment_repo: PunishmentRepositoryInterface,
        logging_service: LoggingServiceInterface,
        history_service: ModerationHistoryServiceInterface,
    ):
        self._repo = punishment_repo
        self._logging_service = logging_service
        self._history_service = history_service
        self._bot: Optional[disnake.Client] = None

    def set_bot(self, bot: disnake.Client) -> None:
        self._bot = bot

    async def warn_user(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        send_dm: bool = True,
        duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            punishment_id = await self._create_punishment(
                moderator=moderator,
                target=target,
                punishment_type=PunishmentType.WARN,
                reason=reason,
                duration_seconds=duration_seconds,
            )

            logger.info(
                f"[WARN] User: {target.name} ({target.id}) | "
                f"Moderator: {moderator.name} ({moderator.id}) | "
                f"Duration: {duration_seconds}s | "
                f"Reason: {reason} | "
                f"Punishment ID: {punishment_id}"
            )

            dm_sent = (
                await self._send_dm(
                    target,
                    "Вам выдано предупреждение",
                    reason,
                )
                if send_dm
                else False
            )

            await self._logging_service.log_moderation_action(
                PunishmentType.WARN,
                moderator,
                target,
                reason,
                duration=duration_seconds,
                punishment_id=punishment_id,
            )

            escalation = await self._history_service.check_auto_escalation(
                target.id,
                target.guild.id,
                PunishmentType.WARN,
            )

            return {
                "success": True,
                "punishment_id": punishment_id,
                "type": PunishmentType.WARN.value,
                "dm_sent": dm_sent,
                "escalation": escalation,
            }

        except Exception as e:
            logger.exception(
                f"[WARN] Failed | target={target.id} "
                f"moderator={moderator.id} reason={reason} error={e}"
            )

            return {
                "success": False,
                "punishment_id": None,
                "type": PunishmentType.WARN.value,
                "dm_sent": False,
                "escalation": False,
            }

    async def mute_user(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        send_dm: bool = True,
        use_timeout: bool = True,
        duration_seconds: Optional[int] = 0,
    ) -> Dict[str, Any]:
        try:
            if not self._can_moderate(moderator, target):
                logger.warning(
                    f"[MUTE] Permission denied | "
                    f"moderator={moderator.id} target={target.id}"
                )
                return False

            duration_seconds = duration_seconds or 0
            duration = max(duration_seconds, 60)

            punishment_id = await self._create_punishment(
                moderator=moderator,
                target=target,
                punishment_type=PunishmentType.MUTE,
                reason=reason,
                duration_seconds=duration,
            )

            logger.info(
                f"[MUTE] User: {target.name} ({target.id}) | "
                f"Moderator: {moderator.name} ({moderator.id}) | "
                f"Duration: {duration}s | "
                f"Reason: {reason} | "
                f"Punishment ID: {punishment_id}"
            )

            success = (
                await self.timeout_user(moderator, target, duration, reason)
                if use_timeout else True
            )

            dm_sent = (
                await self._send_dm(
                    target,
                    "Вам выдан мут",
                    f"{reason}\nДлительность: {self._format_duration(duration)}",
                )
                if send_dm
                else False
            )

            await self._logging_service.log_moderation_action(
                PunishmentType.MUTE,
                moderator,
                target,
                reason,
                duration=duration,
                punishment_id=punishment_id,
            )

            escalation = await self._history_service.check_auto_escalation(
                target.id,
                target.guild.id,
                PunishmentType.MUTE,
            )

            return {
                "success": success,
                "punishment_id": punishment_id,
                "type": PunishmentType.MUTE.value,
                "dm_sent": dm_sent,
                "escalation": escalation,
            }

        except Exception as e:
            logger.exception(
                f"Failed to mute user {target.name} ({target.id}) "
                f"by moderator {moderator.name} ({moderator.id}). "
                f"Reason: {reason}. Error: {e}"
            )
            raise

    async def unmute_user(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str = "Досрочное снятие мута",
    ) -> bool:
        try:
            active = await self._repo.get_active(
                target.guild.id,
                target.id,
                PunishmentType.MUTE.value,
            )

            if not active:
                logger.warning(
                    f"[UNMUTE] Active mute not found for "
                    f"user {target.name} ({target.id})"
                )
                return False

            removed = await self._repo.deactivate(active["id"])

            if removed:
                await self.remove_timeout(moderator, target, reason)

                logger.info(
                    f"[UNMUTE] User: {target.name} ({target.id}) | "
                    f"Moderator: {moderator.name} ({moderator.id}) | "
                    f"Reason: {reason} | "
                    f"Punishment ID: {active['id']}"
                )

                await self._logging_service.log_moderation_action(
                    PunishmentType.UNMUTE,
                    moderator,
                    target,
                    f"Снято: {reason}",
                    punishment_id=active["id"],
                )
            return removed

        except Exception as e:
            logger.exception(
                f"Failed to unmute user {target.name} ({target.id}) "
                f"by moderator {moderator.name} ({moderator.id}). "
                f"Reason: {reason}. Error: {e}"
            )
            raise

    async def kick_user(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        send_dm: bool = True,
    ) -> bool:
        try:
            if not self._can_moderate(moderator, target):
                logger.warning(
                    f"[KICK] Permission denied | "
                    f"moderator={moderator.id} target={target.id}"
                )
                return False

            dm_sent = (
                await self._send_dm(
                    target,
                    "Вас исключили с сервера",
                    reason,
                )
                if send_dm
                else False
            )

            await target.kick(reason=reason)

            punishment_id = await self._create_punishment(
                moderator,
                target,
                PunishmentType.KICK,
                reason,
            )

            logger.info(
                f"[KICK] User: {target.name} ({target.id}) | "
                f"Moderator: {moderator.name} ({moderator.id}) | "
                f"Reason: {reason} | "
                f"Punishment ID: {punishment_id} | "
                f"DM sent: {dm_sent}"
            )

            await self._logging_service.log_moderation_action(
                PunishmentType.KICK,
                moderator,
                target,
                reason,
                duration=0,
                punishment_id=punishment_id,
            )
            return True

        except Exception as e:
            logger.exception(
                f"Failed to kick user {target.name} ({target.id}) "
                f"by moderator {moderator.name} ({moderator.id}). "
                f"Reason: {reason}. Error: {e}"
            )
            return False

    async def ban_user(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str,
        *,
        delete_message_days: int = 1,
        send_dm: bool = True,
        duration_seconds: Optional[int] = None,
    ) -> bool:
        try:
            guild = self._guild_from_actor(moderator)
            if not guild:
                logger.warning("[BAN] Guild not found for moderator=%s", moderator.id)
                return False

            member = (
                guild.get_member(target.id)
                if isinstance(target, disnake.Member)
                else None
            )

            if member and not self._can_moderate(moderator, member):
                logger.warning(
                    "[BAN] Permission denied | moderator=%s target=%s",
                    moderator.id,
                    target.id,
                )
                return False

            if isinstance(target, disnake.Member) and send_dm:
                await self._send_dm(target, "Вас заблокировали на сервере", reason)

            await guild.ban(
                target,
                reason=reason,
                clean_history_duration=timedelta(days=delete_message_days),
            )

            punishment_id = await self._create_punishment(
                moderator,
                target,
                PunishmentType.BAN,
                reason,
                duration_seconds=duration_seconds,
            )

            delete_message_duration = max(0, min(delete_message_days, 9999)) * 86400

            logger.info(
                f"[BAN] User: {target} | "
                f"Moderator: {moderator.id} | "
                f"Reason: {reason} | "
                f"Punishment ID: {punishment_id}"
            )

            await self._logging_service.log_moderation_action(
                PunishmentType.BAN,
                moderator,
                target,
                reason,
                duration=duration_seconds or delete_message_duration,
                punishment_id=punishment_id,
            )
            return True

        except Exception as e:
            logger.exception(
                f"[BAN] Failed | target={getattr(target, 'id', None)} "
                f"moderator={moderator.id} reason={reason} error={e}"
            )
            return False

    async def unban_user(
        self,
        moderator: disnake.Member,
        guild: disnake.Guild,
        user_id: int,
        reason: str = "Досрочное снятие бана",
    ) -> bool:
        try:
            await guild.unban(disnake.Object(id=user_id), reason=reason)

            moderator_member = (
                moderator
                if isinstance(moderator, disnake.Member)
                and moderator.guild.id == guild.id
                else moderator
            )

            logger.info(
                f"[UNBAN] User ID: {user_id} | "
                f"Moderator: {moderator.id} | "
                f"Reason: {reason}"
            )

            await self._logging_service.log_moderation_action(
                PunishmentType.UNBAN,
                moderator_member,
                disnake.Object(id=user_id),
                reason,
            )

            return True

        except Exception as exc:
            logger.exception(
                f"[UNBAN] Failed | user_id={user_id} "
                f"guild_id={guild.id} error={exc}"
            )
            return False

    async def timeout_user(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        duration: int,
        reason: str,
    ) -> bool:
        try:
            if not self._can_moderate(moderator, target):
                logger.warning(
                    "[TIMEOUT] Permission denied | moderator=%s target=%s",
                    moderator.id,
                    target.id,
                )
                return False

            await self._remove_administrator_roles(target, reason)
            await target.timeout(
                duration=timedelta(seconds=duration),
                reason=reason,
            )

            return True

        except Exception as e:
            logger.exception(
                f"[TIMEOUT] Failed | target={target.id} "
                f"moderator={moderator.id} error={e}"
            )
            return False

    async def remove_timeout(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        reason: str = "Досрочное снятие таймаута",
    ) -> bool:
        try:
            if not self._can_moderate(moderator, target):
                logger.warning(
                    "[UNTIMEOUT] Permission denied | moderator=%s target=%s",
                    moderator.id,
                    target.id,
                )
                return False

            await target.timeout(duration=None, reason=reason)

            return True

        except Exception as e:
            logger.exception(
                f"[UNTIMEOUT] Failed | target={target.id} "
                f"moderator={moderator.id} error={e}"
            )
            return False

    async def _create_punishment(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
        punishment_type: PunishmentType,
        reason: str,
        duration_seconds: Optional[int] = None,
    ) -> int:
        guild = self._guild_from_actor(moderator)
        target_guild = getattr(target, "guild", None)
        guild_id = guild.id if guild else target_guild.id if target_guild else 0
        
        if not guild_id:
            raise ValueError("Cannot create punishment without guild context")
        
        expires_at = None

        if duration_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
            
        return await self._repo.add(
            PunishmentDTO(
                guild_id=guild_id,
                user_id=target.id,
                moderator_id=moderator.id,
                type=punishment_type,
                reason=reason,
                duration_seconds=duration_seconds,
                expires_at=expires_at,
            )
        )

    def _can_moderate(
        self,
        moderator: disnake.Member,
        target: disnake.Member,
    ) -> bool:
        if not isinstance(moderator, disnake.Member):
            return True

        if moderator.guild.id != target.guild.id:
            return False

        if moderator.id == target.id:
            return False

        if target.guild_permissions.administrator:
            return moderator.guild_permissions.administrator

        return moderator.top_role.position > target.top_role.position

    async def _remove_administrator_roles(self, target: disnake.Member, reason: str) -> list[int]:
        roles = [
            role
            for role in getattr(target, "roles", [])
            if not role.is_default() and not role.managed and role.permissions.administrator
        ]
        if not roles:
            return []

        guild_me = target.guild.me
        removable_roles = [role for role in roles if guild_me and guild_me.top_role.position > role.position]
        if not removable_roles:
            logger.warning("[MUTE] Administrator roles are not removable target=%s", target.id)
            return []

        await target.remove_roles(*removable_roles, reason=f"Admin roles removed before mute: {reason}")
        removed_ids = [role.id for role in removable_roles]
        logger.info("[MUTE] Removed administrator roles target=%s roles=%s", target.id, removed_ids)
        return removed_ids

    def _guild_from_actor(
        self,
        actor: disnake.Member,
    ) -> Optional[disnake.Guild]:
        return getattr(actor, "guild", None)

    async def _send_dm(
        self,
        target: disnake.Member,
        title: str,
        reason: str,
    ) -> bool:
        try:
            embed = disnake.Embed(
                title=title,
                description=reason,
                color=0xED4245,
                timestamp=datetime.now(timezone.utc),
            )

            await target.send(embed=embed)

            logger.debug(
                f"[DM] Sent to user={target.id} title={title}"
            )
            return True

        except disnake.Forbidden:
            logger.debug(
                f"[DM] Forbidden (closed DMs) user={target.id}"
            )
            return False

        except Exception as exc:
            logger.debug(
                f"[DM] Failed user={target.id} error={exc}"
            )
            return False

    def _format_duration(self, seconds: int) -> str:
        return str(timedelta(seconds=seconds))
    
    

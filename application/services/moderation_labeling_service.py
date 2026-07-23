from application.services.labeling_permission_service import LabelingPermissionService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ModerationLabelingService:
    def __init__(self, repository, permissions: LabelingPermissionService) -> None:
        self._repository = repository
        self._permissions = permissions

    async def set_trusted(self, actor_id: int, guild_id: int, enabled: bool) -> None:
        if not await self._permissions.is_owner(actor_id):
            raise PermissionError("only the trusted owner can change trusted guilds")
        await self._repository.set_trusted(guild_id, enabled)
        await self._repository.audit(guild_id, actor_id, "TRUST_ENABLED" if enabled else "TRUST_DISABLED")
        logger.info("Trusted guild changed guild_id=%s actor_id=%s enabled=%s", guild_id, actor_id, enabled)

    async def set_ai_metrics_access(self, actor_id: int, guild_id: int, enabled: bool) -> None:
        if not await self._permissions.can_manage(actor_id, guild_id):
            raise PermissionError("AI metrics access is not permitted")
        await self._repository.set_ai_metrics_access(guild_id, actor_id, enabled)
        await self._repository.audit(guild_id, actor_id, "AI_METRICS_ENABLED" if enabled else "AI_METRICS_DISABLED")

    async def set_role(self, actor_id: int, guild_id: int, user_id: int, role: str, enabled: bool) -> None:
        normalized_role = role.strip().upper()
        if normalized_role not in {"ADMIN", "LABELER"}:
            raise ValueError("role must be ADMIN or LABELER")
        if not await self._repository.is_trusted(guild_id):
            raise PermissionError("labeling roles are available only for trusted guilds")
        if normalized_role == "ADMIN" and not await self._permissions.is_owner(actor_id):
            raise PermissionError("only the trusted owner can manage administrators")
        if normalized_role == "LABELER" and not await self._permissions.can_manage(actor_id, guild_id):
            raise PermissionError("labeler management is not permitted")
        if enabled:
            await self._repository.assign_role(guild_id, user_id, normalized_role, actor_id)
        else:
            await self._repository.revoke_role(guild_id, user_id, normalized_role)
        await self._repository.audit(guild_id, actor_id, "ROLE_GRANTED" if enabled else "ROLE_REVOKED", user_id)
        logger.info("Labeling role changed guild_id=%s actor_id=%s target_id=%s role=%s enabled=%s", guild_id, actor_id, user_id, normalized_role, enabled)

    async def list_roles(self, actor_id: int, guild_id: int) -> list[dict[str, object]]:
        if not await self._permissions.can_manage(actor_id, guild_id):
            raise PermissionError("role viewing is not permitted")
        return await self._repository.list_roles(guild_id)

    async def get_guild_summary(self, actor_id: int, guild_id: int) -> tuple[bool, list[dict[str, object]]]:
        if not await self._permissions.can_manage(actor_id, guild_id):
            raise PermissionError("guild summary is not permitted")
        return await self._repository.is_trusted(guild_id), await self._repository.list_roles(guild_id)

    async def label(self, actor_id: int, guild_id: int, channel_id: int, message_id: int, author_id: int, label: str, comment: str | None = None, snapshot: str | None = None) -> bool:
        if not await self._permissions.can_label(actor_id, guild_id):
            raise PermissionError("labeling is not permitted")
        created = await self._repository.create_label(guild_id, channel_id, message_id, author_id, label.strip().upper(), comment, actor_id, snapshot)
        if created:
            await self._repository.audit(guild_id, actor_id, "LABEL_CREATED", message_id)
            logger.info("Manual label created guild_id=%s message_id=%s actor_id=%s", guild_id, message_id, actor_id)
        return created

    async def revoke(self, actor_id: int, guild_id: int, message_id: int, label: str) -> bool:
        if not await self._permissions.can_label(actor_id, guild_id):
            raise PermissionError("labeling is not permitted")
        revoked = await self._repository.revoke_label(guild_id, message_id, label.strip().upper(), actor_id)
        if revoked:
            await self._repository.audit(guild_id, actor_id, "LABEL_REVOKED", message_id)
        return revoked

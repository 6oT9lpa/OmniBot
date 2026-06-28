from application.schemas.server_role_purpose_schemas import ServerRolePurposeSchema
from activity.server.dependencies import get_role_purpose_service
from activity.server.schemas.activity import ActivityRolePayload
from activity.server.services.access_service import ActivityAccessService
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ActivityRoleService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()

    async def get_roles(self, guild_id: int, access_token: str) -> dict[str, str]:
        logger.info("Loading legacy Activity role purposes guild_id=%s", guild_id)
        await self._access_service.ensure_admin(access_token, str(guild_id))
        roles = await get_role_purpose_service().get_all_roles(guild_id)
        return {purpose: str(role_id) for purpose, role_id in roles.items()}

    async def save_role(self, payload: ActivityRolePayload, access_token: str) -> dict[str, str]:
        logger.info("Saving legacy Activity role purpose guild_id=%s purpose=%s role_id=%s", payload.guild_id, payload.purpose.value, payload.role_id)
        await self._access_service.ensure_admin(access_token, str(payload.guild_id))
        validated = ServerRolePurposeSchema.model_validate(payload.model_dump())
        await get_role_purpose_service().set_role(
            validated.guild_id,
            validated.purpose,
            validated.role_id,
        )
        roles = await get_role_purpose_service().get_all_roles(validated.guild_id)
        return {purpose: str(role_id) for purpose, role_id in roles.items()}

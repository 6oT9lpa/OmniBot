from activity.server.schemas.activity import ActivityAccess, ActivitySession, ActivityUser
from activity.server.services.access_service import ActivityAccessService
from activity.server.utils.user_type import resolve_user_type


class ActivitySessionService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()

    async def get_session(self, guild_id: str, access_token: str) -> ActivitySession:
        user, access = await self._access_service.fetch_user_and_access_state(access_token, guild_id)
        return ActivitySession(
            user=ActivityUser(**user),
            guild_id=guild_id,
            user_type=resolve_user_type(access),
            access=ActivityAccess(**access),
            is_admin=access["is_admin"],
            access_level=access["access_level"],
            activity_roles=access["activity_roles"],
            permissions=access["permissions"],
            available_modules=access["available_modules"],
        )

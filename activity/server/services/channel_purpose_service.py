from fastapi import HTTPException

from activity.server.dependencies import get_db
from activity.server.schemas.activity import ChannelPurposePayload
from activity.server.services.access_service import ActivityAccessService
from core.domain.channel_purpose import ChannelPurpose
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ChannelPurposeService:
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()

    async def get_channel_purposes(self, guild_id: int, access_token: str) -> dict[str, str]:
        logger.info("Loading channel purposes guild_id=%s", guild_id)
        await self._access_service.ensure_panel_access(access_token, str(guild_id))
        rows = await get_db().fetch_all(
            "SELECT purpose, channel_id FROM server_channel_purposes WHERE guild_id = ?",
            (guild_id,),
        )
        return {row["purpose"]: str(row["channel_id"]) for row in rows}

    async def save_channel_purpose(self, payload: ChannelPurposePayload, access_token: str) -> dict[str, str]:
        logger.info("Saving channel purpose guild_id=%s purpose=%s channel_id=%s", payload.guild_id, payload.purpose.value, payload.channel_id)
        await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "bot-settings", "manage")
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
        return await self.get_channel_purposes(payload.guild_id, access_token)

    async def get_required_purpose_channel(self, guild_id: int, purpose: ChannelPurpose) -> int:
        row = await get_db().fetch_one(
            """
            SELECT channel_id FROM server_channel_purposes
            WHERE guild_id = ? AND purpose = ?
            """,
            (guild_id, purpose.value),
        )
        if not row:
            logger.warning("Required channel purpose missing guild_id=%s purpose=%s", guild_id, purpose.value)
            raise HTTPException(
                status_code=400,
                detail=f"Channel purpose '{purpose.value}' is not configured",
            )
        return int(row["channel_id"])

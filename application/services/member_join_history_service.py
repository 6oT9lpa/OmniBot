from datetime import datetime

from core.interfaces.repositories.member_join_history_repository_interface import MemberJoinHistoryRepositoryInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MemberJoinHistoryService:
    def __init__(self, repository: MemberJoinHistoryRepositoryInterface) -> None:
        self._repository = repository

    async def record_join(self, guild_id: int, user_id: int, joined_at: datetime | None) -> bool:
        if joined_at is None:
            logger.warning("Member join history skipped because joined_at is unavailable guild_id=%s user_id=%s", guild_id, user_id)
            return False
        first_join = await self._repository.record_join(guild_id, user_id, joined_at)
        logger.info("Member join history recorded guild_id=%s user_id=%s join_kind=%s", guild_id, user_id, "first" if first_join else "rejoin")
        return first_join

import csv
import io
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from core.domain.value_objects import PunishmentType
from core.interfaces.repositories import PunishmentRepositoryInterface
from core.interfaces.services import ModerationHistoryServiceInterface
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ModerationHistoryService(ModerationHistoryServiceInterface):
    def __init__(self, punishment_repo: PunishmentRepositoryInterface):
        self._repo = punishment_repo

    async def get(
        self,
        punishment_id: int,
    ) -> Optional[Dict[str, Any]]:
        return await self._repo.get(punishment_id)

    async def list_active_punishments(
        self,
        guild_id: int,
        punishment_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return await self._repo.list_active(guild_id, punishment_type, limit)

    async def get_user_history(
        self,
        user_id: int,
        guild_id: int,
        *,
        limit: int = 50,
        include_active: bool = True,
        include_expired: bool = True,
    ) -> List[Dict[str, Any]]:
        rows = await self._repo.list_for_user(guild_id, user_id, limit)
        return [
            row for row in rows
            if self._include_row(row, include_active, include_expired)
        ]

    async def get_user_punishment_summary(
        self,
        user_id: int,
        guild_id: int,
    ) -> Dict[str, Any]:
        rows = await self._repo.list_for_user(guild_id, user_id, limit=500)
        active = [row for row in rows if row.get("is_active")]
        counts = {
            "warn": 0,
            "mute": 0,
            "kick": 0,
            "ban": 0,
            "timeout": 0,
        }
        for row in rows:
            punishment_type = row.get("type", "unknown")
            if punishment_type in counts:
                counts[punishment_type] += 1
        return {
            "total_count": len(rows),
            "active_count": len(active),
            "warning_count": counts["warn"],
            "mute_count": counts["mute"],
            "kick_count": counts["kick"],
            "ban_count": counts["ban"],
            "timeout_count": counts["timeout"],
        }

    async def check_auto_escalation(
        self,
        user_id: int,
        guild_id: int,
        new_punishment_type: PunishmentType,
    ) -> Optional[str]:
        rows = await self._repo.list_for_user(guild_id, user_id, limit=500)
        active_rows = [row for row in rows if row.get("is_active")]
        warning_count = sum(1 for row in active_rows if row.get("type") == PunishmentType.WARN.value)
        mute_count = sum(1 for row in active_rows if row.get("type") in {PunishmentType.MUTE.value, PunishmentType.TIMEOUT.value})
        kick_count = sum(1 for row in rows if row.get("type") == PunishmentType.KICK.value)

        if new_punishment_type == PunishmentType.WARN and warning_count >= 3:
            return "User has 3 warnings - recommend mute for 10 minutes"
        if new_punishment_type in {PunishmentType.MUTE, PunishmentType.TIMEOUT} and mute_count >= 3:
            return "User has 3 mutes - recommend kick"
        if new_punishment_type == PunishmentType.KICK and kick_count >= 2:
            return "User has 2 kicks - recommend ban"
        return None

    async def revoke_punishment(
        self,
        punishment_id: int,
        moderator_id: int,
        reason: str,
    ) -> bool:
        punishment = await self._repo.get(punishment_id)
        if not punishment:
            return False
        ok = await self._repo.revoke_punishment(punishment_id, moderator_id)
        if not ok:
            return False
        logger.info(
            "Punishment id=%s revoked by moderator id=%s: %s",
            punishment_id,
            moderator_id,
            reason,
        )
        return True

    async def export_punishments_csv(
        self,
        guild_id: int,
        *,
        since: Optional[datetime] = None,
    ) -> str:
        rows = await self._repo.list_active(guild_id, limit=5000)
        if since:
            since_iso = since.isoformat(timespec="seconds")
            rows = [row for row in rows if row.get("created_at", "") >= since_iso]
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id", "guild_id", "user_id", "moderator_id", "type", "reason",
                "duration_seconds", "expires_at", "is_active", "created_at",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
        return output.getvalue()

    def _include_row(
        self,
        row: Dict[str, Any],
        include_active: bool,
        include_expired: bool,
    ) -> bool:
        is_active = bool(row.get("is_active"))
        if not include_active and is_active:
            return False
        if not include_expired and self._is_expired(row):
            return False
        return True

    def _is_expired(self, row: Dict[str, Any]) -> bool:
        expires_at = row.get("expires_at")
        if not expires_at:
            return False
        try:
            return datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc)
        except ValueError:
            return False
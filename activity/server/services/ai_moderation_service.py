"""Activity-facing read/write service for per-guild AI moderation settings."""

from typing import Any

from activity.server.dependencies import get_db
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.discord_service import DiscordService
from activity.server.schemas.ai_moderation_channels import AiModerationChannelsPayload
from activity.server.schemas.ai_moderation_policy import AiModerationPolicyPayload
from core.domain.default_ai_moderation_policy import default_ai_moderation_policy, merge_with_default_ai_moderation_policy
from core.domain.ai_moderation_guild_policy import AiModerationGuildPolicy
from infrastructure.logging import get_logger
from psycopg.types.json import Jsonb

logger = get_logger(__name__)


class AiModerationService:
    """Authorize Activity requests and expose settings plus trusted metrics."""
    def __init__(self) -> None:
        self._access_service = ActivityAccessService()
        self._discord_service = DiscordService()

    async def get_settings(self, guild_id: int, access_token: str) -> dict[str, Any]:
        logger.info("Loading AI moderation settings guild_id=%s", guild_id)
        await self._access_service.ensure_module_access(access_token, str(guild_id), "ai-moderator")
        channels = await get_db().fetch_all("SELECT channel_id FROM ai_moderation_channels WHERE guild_id = ? ORDER BY channel_id", (guild_id,))
        policy_row = await get_db().fetch_one("SELECT policy_json FROM ai_moderation_settings WHERE guild_id = ?", (guild_id,))
        log_row = await get_db().fetch_one("SELECT channel_id FROM server_channel_purposes WHERE guild_id = ? AND purpose = ?", (guild_id, "ai_moderation_log"))
        stored_policy = dict(policy_row["policy_json"]) if policy_row and isinstance(policy_row["policy_json"], dict) else None
        effective_policy, is_default_policy = self._effective_policy(stored_policy, guild_id)
        metrics_enabled = await self._metrics_enabled(guild_id)
        return {
            "guild_id": str(guild_id),
            "channels": [str(row["channel_id"]) for row in channels],
            "log_channel_id": str(log_row["channel_id"]) if log_row else None,
            "policy": effective_policy,
            "is_default_policy": is_default_policy,
            "available_channels": await self._discord_service.list_channels(str(guild_id), "moderation"),
            "metrics_enabled": metrics_enabled,
        }

    async def save_channels(self, payload: AiModerationChannelsPayload, access_token: str) -> dict[str, Any]:
        logger.info(
            "Saving AI moderation channel coverage guild_id=%s channel_count=%s",
            payload.guild_id,
            len(payload.channel_ids),
        )
        await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "ai-moderator", "manage")
        requested_channel_ids = set(payload.channel_ids)
        channel_ids = await self._discord_service.filter_moderation_channel_ids(str(payload.guild_id), requested_channel_ids)
        dropped_channel_ids = sorted(requested_channel_ids - channel_ids)
        if dropped_channel_ids:
            logger.warning(
                "Dropped non-moderatable AI moderation channels guild_id=%s channel_ids=%s",
                payload.guild_id,
                dropped_channel_ids,
            )
        await get_db().execute("DELETE FROM ai_moderation_channels WHERE guild_id = ?", (payload.guild_id,))
        for channel_id in channel_ids:
            await get_db().execute("INSERT INTO ai_moderation_channels (guild_id, channel_id) VALUES (?, ?) ON CONFLICT DO NOTHING", (payload.guild_id, channel_id))
        await get_db().commit()
        logger.info("Saved AI moderation channel coverage guild_id=%s", payload.guild_id)
        return await self.get_settings(payload.guild_id, access_token)

    async def get_metrics(self, guild_id: int, access_token: str) -> dict[str, object]:
        """Return privacy-gated aggregate quality metrics, never message content."""
        await self._access_service.ensure_module_access(access_token, str(guild_id), "ai-moderator")
        if not await self._metrics_enabled(guild_id):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="AI moderation metrics require DM trust from the owner or trusted ADMIN")
        rows = await get_db().fetch_all("SELECT primary_label, labels_json, decision_action, proposed_action, confidence, latency_ms, created_at FROM ai_moderation_events WHERE guild_id = ? ORDER BY created_at DESC LIMIT 5000", (guild_id,))
        manual = await get_db().fetch_all("SELECT event.primary_label, label.label, event.created_at AS event_created_at, label.created_at AS label_created_at FROM ai_moderation_events event JOIN manual_labels label ON label.guild_id = event.guild_id AND label.message_id = event.message_id WHERE event.guild_id = ? AND label.status = 'ACTIVE'", (guild_id,))
        total = len(rows)
        would_delete = sum(row.get("proposed_action") in {"DELETE", "DELETE_WARN"} for row in rows)
        review_count = sum(row["decision_action"] == "REVIEW" for row in rows)
        average_latency = round(sum(int(row.get("latency_ms") or 0) for row in rows) / total) if total else 0
        noisy: dict[str, int] = {}
        for row in rows:
            for label in row.get("labels_json") or []:
                noisy[str(label)] = noisy.get(str(label), 0) + 1
        confused: dict[str, int] = {}
        safe_false_positives = 0
        correction_seconds: list[float] = []
        for row in manual:
            pair = f"{row['primary_label']} → {row['label']}"
            if row["primary_label"] != row["label"]:
                confused[pair] = confused.get(pair, 0) + 1
            if row["label"] == "SAFE" and row["primary_label"] != "SAFE":
                safe_false_positives += 1
            event_created_at, label_created_at = row.get("event_created_at"), row.get("label_created_at")
            if event_created_at and label_created_at and label_created_at >= event_created_at:
                correction_seconds.append((label_created_at - event_created_at).total_seconds())
        return {
            "total_messages": total,
            "would_delete": would_delete,
            "review_count": review_count,
            "average_latency_ms": average_latency,
            "safe_false_positive_rate": round(safe_false_positives / len(manual), 4) if manual else None,
            "confused_classes": self._top_counts(confused),
            "noisy_rules": self._top_counts(noisy),
            "moderator_correction_seconds": round(sum(correction_seconds) / len(correction_seconds)) if correction_seconds else None,
        }

    async def _metrics_enabled(self, guild_id: int) -> bool:
        return await get_db().fetch_one("SELECT 1 FROM ai_moderation_metrics_access WHERE guild_id = ?", (guild_id,)) is not None

    @staticmethod
    def _top_counts(values: dict[str, int]) -> list[dict[str, object]]:
        return [{"name": name, "count": count} for name, count in sorted(values.items(), key=lambda item: item[1], reverse=True)[:8]]

    def _effective_policy(self, stored_policy: dict[str, object] | None, guild_id: int) -> tuple[dict[str, object], bool]:
        if stored_policy is None:
            return default_ai_moderation_policy().model_dump(mode="json"), True
        try:
            policy = AiModerationGuildPolicy.model_validate(stored_policy)
            return merge_with_default_ai_moderation_policy(policy).model_dump(mode="json"), False
        except ValueError:
            logger.warning("Invalid stored AI moderation policy ignored guild_id=%s", guild_id)
            return default_ai_moderation_policy().model_dump(mode="json"), True

    async def save_policy(self, payload: AiModerationPolicyPayload, access_token: str) -> dict[str, Any]:
        logger.info(
            "Saving AI moderation policy guild_id=%s blacklist_count=%s domain_count=%s label_count=%s",
            payload.guild_id,
            len(payload.policy.blacklist_words),
            len(payload.policy.allowed_domains),
            len(payload.policy.labels),
        )
        await self._access_service.ensure_module_access(access_token, str(payload.guild_id), "ai-moderator", "manage")
        await get_db().execute(
            "INSERT INTO ai_moderation_settings (guild_id, policy_json) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET policy_json = excluded.policy_json, updated_at = CURRENT_TIMESTAMP",
            (payload.guild_id, Jsonb(payload.policy.model_dump(mode="json"))),
        )
        await get_db().commit()
        logger.info("Saved AI moderation policy guild_id=%s", payload.guild_id)
        return await self.get_settings(payload.guild_id, access_token)

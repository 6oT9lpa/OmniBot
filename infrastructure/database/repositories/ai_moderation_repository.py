from typing import Mapping

from psycopg.types.json import Jsonb

from core.interfaces.repositories.ai_moderation_repository_interface import AiModerationRepositoryInterface
from infrastructure.database.repositories.base import BaseRepository


class AiModerationRepository(BaseRepository, AiModerationRepositoryInterface):
    async def add_channel(self, guild_id: int, channel_id: int) -> None:
        await self.execute(
            "INSERT INTO ai_moderation_channels (guild_id, channel_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (guild_id, channel_id),
        )

    async def remove_channel(self, guild_id: int, channel_id: int) -> bool:
        result = await self.execute(
            "DELETE FROM ai_moderation_channels WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        )
        return bool(result.rowcount)

    async def list_channels(self, guild_id: int) -> list[int]:
        rows = await self.fetch_all(
            "SELECT channel_id FROM ai_moderation_channels WHERE guild_id = ? ORDER BY channel_id",
            (guild_id,),
        )
        return [int(row["channel_id"]) for row in rows]

    async def get_policy(self, guild_id: int) -> dict[str, object]:
        row = await self.fetch_one("SELECT policy_json FROM ai_moderation_settings WHERE guild_id = ?", (guild_id,))
        payload = row["policy_json"] if row else {}
        return dict(payload) if isinstance(payload, dict) else {}

    async def save_policy(self, guild_id: int, policy: Mapping[str, object]) -> None:
        await self.execute(
            """
            INSERT INTO ai_moderation_settings (guild_id, policy_json)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET policy_json = excluded.policy_json, updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, Jsonb(dict(policy))),
        )

    async def save_event(self, guild_id: int, channel_id: int, message_id: int, user_id: int, risk_score: float, action: str, primary_label: str, labels: tuple[str, ...], status: str) -> None:
        await self.execute(
            """
            INSERT INTO ai_moderation_events (guild_id, channel_id, message_id, user_id, risk_score, decision_action, primary_label, labels_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, message_id) DO UPDATE SET risk_score = excluded.risk_score, decision_action = excluded.decision_action,
              primary_label = excluded.primary_label, labels_json = excluded.labels_json, status = excluded.status
            """,
            (guild_id, channel_id, message_id, user_id, risk_score, action, primary_label, Jsonb(list(labels)), status),
        )

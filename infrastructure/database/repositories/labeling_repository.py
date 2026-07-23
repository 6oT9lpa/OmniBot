from infrastructure.database.repositories.base import BaseRepository


class LabelingRepository(BaseRepository):
    async def is_trusted(self, guild_id: int) -> bool:
        return await self.fetch_one("SELECT 1 FROM trusted_guilds WHERE guild_id = ?", (guild_id,)) is not None

    async def has_role(self, guild_id: int, user_id: int, role: str) -> bool:
        return await self.fetch_one("SELECT 1 FROM labeling_roles WHERE guild_id = ? AND user_id = ? AND role = ?", (guild_id, user_id, role)) is not None

    async def set_trusted(self, guild_id: int, enabled: bool) -> None:
        query = "INSERT INTO trusted_guilds (guild_id) VALUES (?) ON CONFLICT DO NOTHING" if enabled else "DELETE FROM trusted_guilds WHERE guild_id = ?"
        await self.execute_write(query, (guild_id,))

    async def set_ai_metrics_access(self, guild_id: int, actor_id: int, enabled: bool) -> None:
        query = "INSERT INTO ai_moderation_metrics_access (guild_id, granted_by) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET granted_by = excluded.granted_by" if enabled else "DELETE FROM ai_moderation_metrics_access WHERE guild_id = ?"
        await self.execute_write(query, (guild_id, actor_id) if enabled else (guild_id,))

    async def list_roles(self, guild_id: int) -> list[dict[str, object]]:
        return await self.fetch_all(
            "SELECT user_id, role, assigned_by, created_at FROM labeling_roles WHERE guild_id = ? ORDER BY role, user_id",
            (guild_id,),
        )

    async def assign_role(self, guild_id: int, user_id: int, role: str, actor_id: int) -> None:
        await self.execute_write("INSERT INTO labeling_roles (guild_id,user_id,role,assigned_by) VALUES (?,?,?,?) ON CONFLICT DO NOTHING", (guild_id,user_id,role,actor_id))

    async def revoke_role(self, guild_id: int, user_id: int, role: str) -> bool:
        return bool((await self.execute("DELETE FROM labeling_roles WHERE guild_id=? AND user_id=? AND role=?", (guild_id,user_id,role))).rowcount)

    async def audit(self, guild_id: int, actor_id: int, action: str, target_id: int | None = None) -> None:
        await self.execute_write("INSERT INTO labeling_audit (guild_id,actor_id,action,target_id) VALUES (?,?,?,?)", (guild_id,actor_id,action,target_id))

    async def create_label(self, guild_id: int, channel_id: int, message_id: int, author_id: int, label: str, comment: str | None, actor_id: int, snapshot: str | None) -> bool:
        result = await self.execute("""INSERT INTO manual_labels (guild_id,channel_id,message_id,author_id,label,comment,labeled_by,content_snapshot,source,schema_version)
            VALUES (?,?,?,?,?,?,?,?, 'MANUAL', 1) ON CONFLICT (guild_id,message_id,label) DO NOTHING""", (guild_id,channel_id,message_id,author_id,label,comment,actor_id,snapshot))
        return bool(result.rowcount)

    async def revoke_label(self, guild_id: int, message_id: int, label: str, actor_id: int) -> bool:
        result = await self.execute("""UPDATE manual_labels SET status='REVOKED' WHERE guild_id=? AND message_id=? AND label=?
            AND status='ACTIVE' AND labeled_by=?""", (guild_id,message_id,label,actor_id))
        return bool(result.rowcount)

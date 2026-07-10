from typing import List, Dict, Any
import disnake

from infrastructure.logging import get_logger
from presentation.views.roles_panel_management.helpers import is_safe_self_assignable_role

logger = get_logger(__name__)


class RolePanelReactionView:
    def __init__(self, message: disnake.Message, buttons_data: List[Dict[str, Any]], role_service):
        self._message = message
        self._buttons_data = buttons_data[:25]
        self._role_service = role_service
        self._role_emoji_map: Dict[str, int] = {}

    async def setup(self):
        self._role_emoji_map = self._build_role_emoji_map(self._buttons_data)
        await self._ensure_reactions(self._role_emoji_map.keys())

    async def reload(self, message: disnake.Message, buttons_data: List[Dict[str, Any]]) -> None:
        """Refresh listener data without clearing all user reactions."""

        old_emojis = set(self._role_emoji_map)
        self._message = message
        self._buttons_data = buttons_data[:25]
        self._role_emoji_map = self._build_role_emoji_map(self._buttons_data)

        removed_emojis = old_emojis - set(self._role_emoji_map)
        for emoji in removed_emojis:
            await self._clear_reaction(emoji)

        await self._ensure_reactions(self._role_emoji_map.keys())
        logger.info("Reloaded reaction panel for message id=%s", self._message.id)

    def _build_role_emoji_map(self, buttons_data: List[Dict[str, Any]]) -> Dict[str, int]:
        role_emoji_map: Dict[str, int] = {}
        for btn_data in buttons_data:
            emoji = btn_data.get("emoji") or "🎭"
            if isinstance(emoji, str):
                if emoji in role_emoji_map:
                    logger.warning("Duplicate reaction emoji %s skipped for role id=%s", emoji, btn_data["role_id"])
                    continue
                role_emoji_map[emoji] = btn_data["role_id"]
        return role_emoji_map

    async def _ensure_reactions(self, emojis) -> None:
        for emoji in emojis:
            try:
                await self._message.add_reaction(emoji)
                logger.info("Ensured reaction %s for message id=%s", emoji, self._message.id)
            except Exception as exc:
                logger.error("Failed to add reaction %s: %s", emoji, exc)

    async def _clear_reaction(self, emoji: str) -> None:
        try:
            await self._message.clear_reaction(emoji)
            logger.info("Cleared stale reaction %s for message id=%s", emoji, self._message.id)
        except Exception as exc:
            logger.error("Failed to clear reaction %s: %s", emoji, exc)

    async def handle_reaction(self, payload: disnake.RawReactionActionEvent):
        if payload.message_id != self._message.id:
            return

        emoji = str(payload.emoji)
        if emoji not in self._role_emoji_map:
            return

        guild = self._message.guild
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        role_id = self._role_emoji_map[emoji]
        role = guild.get_role(role_id)

        if not role:
            logger.warning("Role id=%s not found for reaction %s", role_id, emoji)
            return

        try:
            if not is_safe_self_assignable_role(guild, role):
                logger.warning("Blocked unsafe reaction-panel role id=%s for member id=%s", role_id, member.id)
                return

            if role in member.roles:
                await member.remove_roles(role, reason="Role removed via reaction panel")
                logger.info("Removed role id=%s from member id=%s via reaction", role_id, member.id)
            else:
                await member.add_roles(role, reason="Role assigned via reaction panel")
                logger.info("Assigned role id=%s to member id=%s via reaction", role_id, member.id)
        except Exception as exc:
            logger.error("Error handling reaction for role id=%s: %s", role_id, exc)


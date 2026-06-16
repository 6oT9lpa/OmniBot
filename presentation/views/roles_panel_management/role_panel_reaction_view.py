from typing import List, Dict, Any
import disnake

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RolePanelReactionView:
    def __init__(self, message: disnake.Message, buttons_data: List[Dict[str, Any]], role_service):
        self._message = message
        self._buttons_data = buttons_data[:25]
        self._role_service = role_service
        self._role_emoji_map: Dict[str, int] = {}

    async def setup(self):
        for btn_data in self._buttons_data:
            emoji = btn_data.get("emoji") or "🎭"
            if isinstance(emoji, str):
                try:
                    await self._message.add_reaction(emoji)
                    self._role_emoji_map[emoji] = btn_data["role_id"]
                    logger.info("Added reaction %s for role id=%s", emoji, btn_data["role_id"])
                except Exception as exc:
                    logger.error("Failed to add reaction %s: %s", emoji, exc)

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
            if guild.me.top_role.position <= role.position:
                logger.warning("Cannot assign role id=%s to member id=%s: bot role is lower", role_id, member.id)
                return

            if role in member.roles:
                await member.remove_roles(role, reason="Role removed via reaction panel")
                logger.info("Removed role id=%s from member id=%s via reaction", role_id, member.id)
            else:
                await member.add_roles(role, reason="Role assigned via reaction panel")
                logger.info("Assigned role id=%s to member id=%s via reaction", role_id, member.id)
        except Exception as exc:
            logger.error("Error handling reaction for role id=%s: %s", role_id, exc)

    async def clear_reactions(self):
        try:
            await self._message.clear_reactions()
            logger.info("Cleared reactions for message id=%s", self._message.id)
        except Exception as exc:
            logger.error("Failed to clear reactions: %s", exc)

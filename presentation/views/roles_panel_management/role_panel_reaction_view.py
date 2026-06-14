from typing import List, Dict, Any
import disnake

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RolePanelReactionView:
    def __init__(self, message: disnake.Message, buttons_data: List[Dict[str, Any]], role_service):
        self._message = message
        self._buttons_data = buttons_data
        self._role_service = role_service
        self._role_emoji_map: Dict[str, int] = {}

    async def setup(self):
        for btn_data in self._buttons_data:
            emoji = btn_data.get("emoji") or "🎭"
            if isinstance(emoji, str):
                try:
                    await self._message.add_reaction(emoji)
                    self._role_emoji_map[emoji] = btn_data["role_id"]
                    logger.info(f"Added reaction {emoji} for role {btn_data['role_id']}")
                except Exception as e:
                    logger.error(f"Failed to add reaction {emoji}: {e}")

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
            logger.warning(f"Role {role_id} not found for reaction {emoji}")
            return

        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Role removed via reaction panel")
                logger.info(f"Removed role {role.name} from {member} via reaction")
            else:
                if guild.me.top_role.position <= role.position:
                    logger.warning(f"Cannot assign role {role.name}: bot role is lower")
                    return
                await member.add_roles(role, reason="Role assigned via reaction panel")
                logger.info(f"Assigned role {role.name} to {member} via reaction")
        except Exception as e:
            logger.error(f"Error handling reaction for role {role_id}: {e}")

    async def clear_reactions(self):
        try:
            await self._message.clear_reactions()
            logger.info(f"Cleared reactions for message {self._message.id}")
        except Exception as e:
            logger.error(f"Failed to clear reactions: {e}")
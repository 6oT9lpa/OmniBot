from typing import List, Optional, Dict, Any
import disnake
from datetime import datetime, timezone, timedelta

from infrastructure.config import BotConfig
from infrastructure.database.repositories.role_repository import RoleRepository
from infrastructure.database.repositories.role_panel_message_repository import RolePanelMessageRepository
from infrastructure.database.repositories.role_panel_button_repository import RolePanelButtonRepository
from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView

logger = get_logger(__name__)


def get_msk_timestamp() -> str:
    """Получить текущий timestamp в МСК"""
    msk_tz = timezone(timedelta(hours=3))
    return datetime.now(msk_tz).strftime("%Y-%m-%d %H:%M:%S")


class RoleService:
    def __init__(self, role_repo: RoleRepository, config: BotConfig):
        self.role_repo = role_repo
        self.config = config
        self._bot: Optional[disnake.Client] = None
        self._panel_message_repo: Optional[RolePanelMessageRepository] = None
        self._panel_button_repo: Optional[RolePanelButtonRepository] = None

    def set_bot(self, bot: disnake.Client):
        self._bot = bot

    def set_panel_repositories(
        self,
        panel_message_repo: RolePanelMessageRepository,
        panel_button_repo: RolePanelButtonRepository,
    ):
        self._panel_message_repo = panel_message_repo
        self._panel_button_repo = panel_button_repo

    async def assign_auto_roles(self, member: disnake.Member) -> List[disnake.Role]:
        """Выдать автоматические роли новому участнику"""
        if not self._bot:
            logger.error("Bot not set in RoleService")
            return []

        auto_role_ids = await self.role_repo.get_auto_assign_roles()
        assigned = []

        for role_id in auto_role_ids:
            role = member.guild.get_role(role_id)
            if role:
                if member.guild.me.top_role.position > role.position:
                    try:
                        await member.add_roles(role, reason="Автовыдача при входе")
                        assigned.append(role)
                        logger.info(f"Assigned role {role.name} to {member}")
                    except Exception as e:
                        logger.error(f"Failed to assign role {role_id}: {e}")
                else:
                    logger.warning(f"Cannot assign role {role.name}: bot role is lower")

        return assigned

    async def sync_roles(self, guild: disnake.Guild) -> int:
        """Синхронизировать роли с Discord"""
        discord_roles = []

        for role in guild.roles:
            if role.is_default() or role.managed:
                continue
            discord_roles.append({
                "id": role.id,
                "name": role.name,
                "color": role.color.value,
                "position": role.position,
                "permissions": role.permissions.value,
            })

        return await self.role_repo.sync_from_discord(discord_roles)


    async def get_all_roles(self) -> List[Dict[str, Any]]:
        return await self.role_repo.get_all_roles()

    async def get_public_roles(self) -> List[Dict[str, Any]]:
        return await self.role_repo.get_public_roles()

    async def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        return await self.role_repo.get_role(role_id)

    async def set_auto_assign(self, role_id: int, is_auto_assign: bool) -> bool:
        return await self.role_repo.set_auto_assign(role_id, is_auto_assign)

    async def set_role_public(self, role_id: int, is_public: bool) -> bool:
        existing = await self.role_repo.get_role(role_id)
        if not existing:
            logger.warning(f"set_role_public: role {role_id} not found in DB")
            return False
        await self.role_repo.set_public(role_id, is_public)
        logger.info(f"Role {role_id} public set to {is_public}")
        return True

    async def create_role_panel(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        embed_title: str,
        embed_description: str,
        embed_color: int,
        created_by: int,
    ) -> int:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        return await self._panel_message_repo.create(
            guild_id, channel_id, message_id,
            embed_title, embed_description, embed_color, created_by,
        )

    async def delete_panel(self, message_id: int) -> bool:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            logger.warning(f"delete_panel: panel {message_id} not found")
            return False
        return await self._panel_message_repo.delete_by_message(message_id)

    async def add_button_to_panel(
        self,
        message_id: int,
        role_id: int,
        role_name: str,
        emoji: str = None,
    ) -> bool:
        if not self._panel_button_repo or not self._panel_message_repo:
            raise ValueError("Panel repositories not set")

        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            logger.warning(f"Panel not found for message {message_id}")
            return False

        await self._panel_button_repo.add(panel["id"], role_id, role_name, emoji)
        return True

    async def remove_button_from_panel(self, message_id: int, role_id: int) -> bool:
        if not self._panel_button_repo or not self._panel_message_repo:
            raise ValueError("Panel repositories not set")

        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            return False

        return await self._panel_button_repo.remove(panel["id"], role_id)

    async def get_panel_buttons(self, message_id: int) -> List[Dict[str, Any]]:
        if not self._panel_button_repo or not self._panel_message_repo:
            raise ValueError("Panel repositories not set")

        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            return []

        return await self._panel_button_repo.get_all(panel["id"])

    async def refresh_panel_view(self, message_id: int, channel: disnake.TextChannel) -> bool:
        if not self._bot:
            return False

        try:
            message = await channel.fetch_message(message_id)
            if not message:
                return False

            buttons = await self.get_panel_buttons(message_id)
            if not buttons:
                return False

            view = RolePanelView(buttons, message_id, self)
            await message.edit(view=view)
            logger.info(f"Refreshed panel view for message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh panel view: {e}")
            return False
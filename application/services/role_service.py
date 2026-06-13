from typing import List, Optional, Dict, Any
import disnake

from infrastructure.config import BotConfig
from infrastructure.database.repositories import RoleRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RoleService:
    def __init__(self, role_repo: RoleRepository, config: BotConfig):
        self.role_repo = role_repo
        self.config = config
        self._bot: Optional[disnake.Client] = None

    def set_bot(self, bot: disnake.Client):
        """Установить бота (после создания)"""
        self._bot = bot

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
            if role.is_default():
                continue
            discord_roles.append({
                "id": role.id,
                "name": role.name,
            })
        
        await self.role_repo.sync_from_discord(discord_roles)
        return len(discord_roles)
    
    async def get_all_roles(self) -> List[Dict[str, Any]]:
        """Получить все роли из БД"""
        return await self.role_repo.get_all_roles()
    
    async def get_public_roles(self) -> List[Dict[str, Any]]:
        """Получить публичные роли из БД"""
        return await self.role_repo.get_public_roles()
    
    async def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        """Получить роль по ID"""
        return await self.role_repo.get_role(role_id)
    
    async def set_auto_assign(self, role_id: int, is_auto_assign: bool) -> bool:
        """Установить флаг автовыдачи"""
        return await self.role_repo.set_auto_assign(role_id, is_auto_assign)
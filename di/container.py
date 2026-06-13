from typing import Optional

from infrastructure.config import get_config, BotConfig
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.role_repository import RoleRepository
from application.services.role_service import RoleService


class Container:
    def __init__(self):
        self.config: BotConfig = get_config()
        
        self._database: Optional[DatabaseManager] = None
        self._role_repo: Optional[RoleRepository] = None
        self._role_service: Optional[RoleService] = None

    async def get_database(self) -> DatabaseManager:
        """Получить менеджер БД"""
        if not self._database:
            self._database = DatabaseManager(self.config.database_url)
            await self._database.connect()
            await self._database.initialize()
        return self._database
    
    async def get_role_repository(self) -> RoleRepository:
        """Получить репозиторий ролей"""
        if not self._role_repo:
            db = await self.get_database()
            self._role_repo = RoleRepository(db, self.config.discord_guild_id)
        return self._role_repo
    
    async def get_role_service(self) -> RoleService:
        """Получить сервис ролей"""
        if not self._role_service:
            repo = await self.get_role_repository()
            self._role_service = RoleService(repo, self.config)
        return self._role_service
    
    async def shutdown(self):
        """Закрытие ресурсов"""
        if self._database:
            await self._database.close()

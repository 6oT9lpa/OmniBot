from typing import Optional

from infrastructure.config import get_config, BotConfig
from infrastructure.database import DatabaseManager
from infrastructure.database.repositories.role_repository import RoleRepository
from infrastructure.database.repositories.role_panel_message_repository import RolePanelMessageRepository
from infrastructure.database.repositories.role_panel_button_repository import RolePanelButtonRepository
from application.services.role_service import RoleService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class Container:
    def __init__(self):
        self.config: BotConfig = get_config()
        
        self._database: Optional[DatabaseManager] = None
        self._role_repo: Optional[RoleRepository] = None
        self._role_service: Optional[RoleService] = None
        self._panel_message_repo: Optional[RolePanelMessageRepository] = None
        self._panel_button_repo: Optional[RolePanelButtonRepository] = None

        logger.info("DI Container initialized")

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
    
    async def get_panel_message_repository(self) -> RolePanelMessageRepository:
        """Получить репозиторий панелей"""

        if not self._panel_message_repo:
            db = await self.get_database()
            self._panel_message_repo = RolePanelMessageRepository(db)
        return self._panel_message_repo
    
    async def get_panel_button_repository(self) -> RolePanelButtonRepository:
        """Получить репозиторий кнопок панелей"""

        if not self._panel_button_repo:
            db = await self.get_database()
            self._panel_button_repo = RolePanelButtonRepository(db)
        return self._panel_button_repo
    
    async def get_role_service(self) -> RoleService:
        """Получить сервис ролей"""

        if not self._role_service:
            repo = await self.get_role_repository()
            self._role_service = RoleService(repo, self.config)
            
            panel_message_repo = await self.get_panel_message_repository()
            panel_button_repo = await self.get_panel_button_repository()
            self._role_service.set_panel_repositories(panel_message_repo, panel_button_repo)
            
            logger.info("RoleService created with panel repositories")
            
        return self._role_service
    
    async def shutdown(self):
        """Закрытие ресурсов"""

        if self._database:
            await self._database.close()

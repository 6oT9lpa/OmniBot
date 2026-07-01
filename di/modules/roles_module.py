from typing import Optional

from disnake.ext import commands

from application.services.role_service import RoleService
from application.services.server_role_purpose_service import ServerRolePurposeService
from infrastructure.logging import get_logger
from presentation.cogs import RolesCog

logger = get_logger(__name__)


class RolesModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[RolesCog] = None

    async def get_role_service(self) -> RoleService:
        return await self._container.get_role_service()

    async def get_role_purpose_service(self) -> ServerRolePurposeService:
        return await self._container.get_server_role_purpose_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[RolesCog]:
        if self._cog:
            return self._cog

        try:
            role_service = await self.get_role_service()
            role_purpose_service = await self.get_role_purpose_service()
            self._cog = RolesCog(bot, role_service, role_purpose_service)
            logger.info("RolesCog created and configured")
            return self._cog
        except Exception as exc:
            logger.error("Failed to create RolesCog: %s", exc)
            return None

    async def shutdown(self):
        self._cog = None
        logger.info("RolesModule shutdown")

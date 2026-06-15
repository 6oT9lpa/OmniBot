from typing import Optional

from disnake.ext import commands

from application.services import AuditLogService, LoggingService
from infrastructure.logging import get_logger
from presentation.cogs import LoggingCog

logger = get_logger(__name__)


class LoggingModule:
    def __init__(self, container):
        self._container = container
        self._cog: Optional[LoggingCog] = None

    async def get_audit_log_service(self) -> AuditLogService:
        return await self._container.get_audit_log_service()

    async def get_logging_service(self) -> LoggingService:
        return await self._container.get_logging_service()

    async def get_cog(self, bot: commands.Bot) -> Optional[LoggingCog]:
        if self._cog:
            return self._cog

        try:
            logging_service = await self.get_logging_service()
            audit_log_service = await self.get_audit_log_service()
            self._cog = LoggingCog(logging_service, audit_log_service)
            logger.info("LoggingCog created and configured")
            return self._cog
        except Exception as exc:
            logger.error("Failed to create LoggingCog: %s", exc)
            return None

    async def shutdown(self):
        self._cog = None
        logger.info("LoggingModule shutdown")

from typing import Optional

from fastapi import Header, HTTPException

from application.services import ServerRolePurposeService
from infrastructure.config import get_config
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories import ServerRolePurposeRepository
from infrastructure.logging import get_logger


logger = get_logger(__name__)


_db: Optional[DatabaseManager] = None
_role_purpose_service: Optional[ServerRolePurposeService] = None


async def initialize_activity_dependencies() -> None:
    global _db, _role_purpose_service
    config = get_config()
    logger.info("Initializing Activity PostgreSQL dependencies")
    _db = DatabaseManager(config.database_url)
    await _db.initialize()
    _role_purpose_service = ServerRolePurposeService(ServerRolePurposeRepository(_db))
    logger.info("Activity database dependencies initialized")


async def shutdown_activity_dependencies() -> None:
    if _db:
        logger.info("Closing Activity database dependency")
        await _db.close()
        logger.info("Activity database dependency closed")


def get_db() -> DatabaseManager:
    if _db is None:
        logger.error("Activity database requested before initialization")
        raise HTTPException(status_code=503, detail="Database is not initialized")
    return _db


def get_role_purpose_service() -> ServerRolePurposeService:
    if _role_purpose_service is None:
        logger.error("Role purpose service requested before initialization")
        raise HTTPException(status_code=503, detail="Role purpose service is not initialized")
    return _role_purpose_service


def require_bearer_token(authorization: str = Header(default="")) -> str:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        logger.warning("Activity request rejected because bearer token is missing")
        raise HTTPException(status_code=401, detail="Bearer token is required")
    token = authorization[len(prefix):].strip()
    if not token or len(token) > 4096 or any(character.isspace() for character in token):
        logger.warning("Activity request rejected because bearer token is malformed")
        raise HTTPException(status_code=401, detail="Bearer token is invalid")
    return token

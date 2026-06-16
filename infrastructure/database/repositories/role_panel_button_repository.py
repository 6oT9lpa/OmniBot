from typing import List, Optional, Dict, Any

from core.interfaces.repositories import RolePanelButtonRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RolePanelButtonRepository(RolePanelButtonRepositoryInterface, BaseRepository):
    _TABLE_NAME = "role_panel_buttons"
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)
    
    async def add(
        self,
        panel_message_id: int,
        role_id: int,
        role_name: str,
        emoji: str = None,
        position: int = 0
    ) -> int:
        existing = await self.get(panel_message_id, role_id)
        if existing:
            logger.debug(f"Button for role {role_id} already exists in panel {panel_message_id}")
            return existing["id"]
        
        data = {
            "panel_message_id": panel_message_id,
            "role_id": role_id,
            "role_name": role_name,
            "emoji": emoji,
            "position": position
        }
        return await self.insert(data)
    
    async def remove(self, panel_message_id: int, role_id: int) -> bool:
        query = f"""
            DELETE FROM {self._TABLE_NAME} 
            WHERE panel_message_id = ? AND role_id = ?
        """
        cursor = await self.execute(query, (panel_message_id, role_id))
        await self.commit()
        return cursor.rowcount > 0
    
    async def get_all(self, panel_message_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM role_panel_buttons 
            WHERE panel_message_id = ?
            ORDER BY position ASC, id ASC
        """
        return await self.fetch_all(query, (panel_message_id,))
    
    async def get(self, panel_message_id: int, role_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT * FROM role_panel_buttons 
            WHERE panel_message_id = ? AND role_id = ?
        """
        return await self.fetch_one(query, (panel_message_id, role_id))
    
    async def clear_all(self, panel_message_id: int) -> int:
        query = f"DELETE FROM {self._TABLE_NAME} WHERE panel_message_id = ?"
        cursor = await self.execute(query, (panel_message_id,))
        await self.commit()
        return cursor.rowcount
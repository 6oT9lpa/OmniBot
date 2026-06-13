from typing import List, Dict, Any

from presentation.views import BaseView
from presentation.views import RoleButton
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RolePanelView(BaseView):
    def __init__(self, buttons_data: List[Dict[str, Any]], message_id: int, role_service):
        super().__init__(timeout=None)
        self._buttons_data = buttons_data
        self._message_id = message_id
        self._role_service = role_service
        self._build_buttons()
        logger.debug(f"Created persistent panel with {len(buttons_data)} buttons")
    
    def _build_buttons(self):
        for btn_data in self._buttons_data:
            button = RoleButton(
                role_id=btn_data["role_id"],
                role_name=btn_data["role_name"],
                emoji=btn_data.get("emoji")
            )
            self.add_item(button)
    
    async def refresh(self):
        new_buttons = await self._role_service.get_panel_buttons(self._message_id)
        self._buttons_data = new_buttons
        self.clear_items()
        self._build_buttons()
        logger.debug(f"Refreshed panel {self._message_id} with {len(new_buttons)} buttons")
from typing import List, Dict, Any

from infrastructure.logging import get_logger
from presentation.views.base import BaseView

logger = get_logger(__name__)


class RolePanelHybridView(BaseView):
    def __init__(self, buttons_data: List[Dict[str, Any]], message_id: int, role_service, use_reactions: bool = False):
        super().__init__(timeout=None)
        self._buttons_data = buttons_data
        self._message_id = message_id
        self._role_service = role_service
        self._use_reactions = use_reactions
        self._build_buttons()

    def _build_buttons(self):
        if self._use_reactions:
            return
        
        from presentation.views.role_button import RoleButton
        
        for btn_data in self._buttons_data:
            button = RoleButton(
                role_id=btn_data["role_id"],
                role_name=btn_data["role_name"],
                emoji=btn_data.get("emoji")
            )
            self.add_item(button)

    def reload_buttons(self):
        if not self._use_reactions:
            self.clear_items()
            self._build_buttons()
        logger.debug(f"Reloaded panel {self._message_id} with {len(self._buttons_data)} buttons")
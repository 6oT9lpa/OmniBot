from typing import List, Dict, Any

from presentation.views.base import BaseView
from presentation.views.role_button import RoleButton
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RolePanelView(BaseView):
    def __init__(self, buttons_data: List[Dict[str, Any]], message_id: int, role_service):
        super().__init__(timeout=None)
        self._buttons_data = buttons_data[:25]
        self._message_id = message_id
        self._role_service = role_service
        self._build_buttons()
        logger.debug("Created persistent panel with %s buttons", len(self._buttons_data))

    def _build_buttons(self):
        for btn_data in self._buttons_data:
            button = RoleButton(
                role_id=btn_data["role_id"],
                role_name=btn_data["role_name"],
                emoji=btn_data.get("emoji")
            )
            self.add_item(button)

    def reload_buttons(self):
        self.clear_items()
        self._build_buttons()
        logger.debug("Reloaded panel %s with %s buttons", self._message_id, len(self._buttons_data))

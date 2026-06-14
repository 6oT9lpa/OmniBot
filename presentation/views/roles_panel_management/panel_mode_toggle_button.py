import disnake

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PanelModeToggleButton(disnake.ui.Button):
    def __init__(self, use_reactions: bool = False, row: int = 2):
        mode_text = "реакции" if use_reactions else "кнопки"
        super().__init__(
            label=f"Режим: {mode_text}",
            style=disnake.ButtonStyle.success if use_reactions else disnake.ButtonStyle.secondary,
            custom_id="toggle_reaction_mode",
            row=row,
        )
        self._use_reactions = use_reactions
        logger.debug(f"PanelModeToggleButton initialized: use_reactions={use_reactions}, row={row}")

    def toggle(self) -> bool:
        """Переключить режим и обновить внешний вид кнопки. Возвращает новое состояние."""
        
        self._use_reactions = not self._use_reactions
        mode_text = "реакции" if self._use_reactions else "кнопки"
        self.label = f"Режим: {mode_text}"
        self.style = (
            disnake.ButtonStyle.success
            if self._use_reactions
            else disnake.ButtonStyle.secondary
        )
        logger.debug(f"Panel mode toggled: use_reactions={self._use_reactions}")
        return self._use_reactions

    @property
    def use_reactions(self) -> bool:
        return self._use_reactions
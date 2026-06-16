import disnake
from typing import Optional

from core.domain.value_objects import PunishmentType
from application.services import ModerationHistoryService, LoggingService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PunishmentListView(disnake.ui.View):
    def __init__(self, history_service: ModerationHistoryService, rows: list, logging_service: Optional[LoggingService] = None):
        super().__init__(timeout=300)
        self._history_service = history_service
        self._logging_service = logging_service
        self.rows = rows[:25]
        options = [
            disnake.SelectOption(
                label=f"#{row['id']} {row['type']} user:{row['user_id']}",
                description=(row.get("reason") or "No reason")[:100],
                value=str(row["id"]),
            )
            for row in self.rows
        ]
        self.select = disnake.ui.StringSelect(
            custom_id="punishment_select",
            placeholder="Select punishment to revoke",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._on_select
        self.add_item(self.select)

    async def _on_select(self, interaction: disnake.MessageInteraction):
        punishment_value = interaction.data["values"][0]
        punishment_id = int(punishment_value)
        await interaction.response.send_modal(RevokePunishmentModal(punishment_id, self))


class RevokePunishmentModal(disnake.ui.Modal):
    reason = disnake.ui.TextInput(
        label="Revoke reason",
        placeholder="Mistake",
        style=disnake.TextInputStyle.paragraph,
        required=True,
    )

    def __init__(self, punishment_id: int, parent: PunishmentListView):
        super().__init__(
            title="Revoke punishment",
            custom_id=f"revoke:{punishment_id}",
            components=[self.reason],
        )
        self._punishment_id = punishment_id
        self._parent = parent

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = self.reason.value or "Early punishment revocation"
        
        if self._parent._logging_service:
            punishment = await self._parent._history_service.get(self._punishment_id)
            if punishment:
                target_user = disnake.Object(id=punishment["user_id"])
                await self._parent._logging_service.log_moderation_action(
                    PunishmentType(punishment["type"]),
                    interaction.author,
                    target_user,
                    f"Revoked: {reason}",
                )
        
        ok = await self._parent._history_service.revoke_punishment(
            self._punishment_id,
            interaction.author.id,
            reason,
        )
        await interaction.response.send_message(
            embed=disnake.Embed(
                title="Punishment revoked" if ok else "Failed to revoke punishment",
                description=f"Record #{self._punishment_id}",
                color=disnake.Color.green() if ok else disnake.Color.red(),
            ),
            ephemeral=True,
        )
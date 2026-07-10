import disnake
from disnake.ui import Button
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RoleButton(Button):
    def __init__(self, role_id: int, role_name: str, emoji: str = None):
        label = role_name[:80]
        if emoji:
            label = f"{emoji} {label}"

        super().__init__(
            label=label,
            style=disnake.ButtonStyle.primary,
            custom_id=f"persistent_role_{role_id}"
        )

        self.role_id = role_id
    
    async def callback(self, interaction: disnake.MessageInteraction):
        if not interaction.guild or not isinstance(interaction.user, disnake.Member):
            await interaction.response.send_message("This control is available only in a server.", ephemeral=True)
            return
        user = interaction.user
        logger.info(f"Role button clicked: {self.label} by {user}")

        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("Роль не найдена", ephemeral=True)
            return
        if role.managed or int(role.permissions.value) != 0:
            logger.warning("Blocked unsafe self-assignable role id=%s", role.id)
            await interaction.response.send_message("This role cannot be assigned through a role panel.", ephemeral=True)
            return
        
        member = interaction.user
        if interaction.guild.me is None or interaction.guild.me.top_role.position <= role.position:
            await interaction.response.send_message("I cannot change this role because it is above my highest role.", ephemeral=True)
            return
        if role in member.roles:
            await member.remove_roles(role, reason="Снятие через панель ролей")
            await interaction.response.send_message(f"Роль **{role.name}** снята", ephemeral=True)
            logger.info(f"Role {role.name} removed from {member}")
            
        else:
            if interaction.guild.me.top_role.position <= role.position:
                await interaction.response.send_message("Не могу выдать эту роль (она выше моей)", ephemeral=True)
                return
            
            await member.add_roles(role, reason="Выдача через панель ролей")
            await interaction.response.send_message(f"Роль **{role.name}** выдана", ephemeral=True)
            logger.info(f"Role {role.name} assigned to {member}")

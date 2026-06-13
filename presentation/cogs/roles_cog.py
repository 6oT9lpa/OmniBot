import disnake
from disnake.ext import commands

from application.services.role_service import RoleService
from infrastructure.logging import get_logger
from presentation.views import RolePanelView, RolePanelPaginatedView

logger = get_logger(__name__)


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, role_service: RoleService):
        self._bot = bot
        self._role_service = role_service
        logger.info("RolesCog initialized")

    @property
    def role_service(self):
        """Getter для доступа к сервису"""
        return self._role_service
    
    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Автовыдача роли новому учаснику"""

        logger.info(f"New member joined: {member}")
        assigned = await self.role_service.assign_auto_roles(member)
        if assigned:
            role_names = ", ".join([r.name for r in assigned])
            logger.info(f"Assigned roles {role_names} to {member}")

    @commands.slash_command(name="sync_roles", description="Синхронизировать роли с Discord")
    async def sync_roles(self, ctx: disnake.ApplicationCommandInteraction):
        """Синхронизировать роли сервера с БД"""

        logger.info(f"sync_roles command invoked by {ctx.author}")
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return
        
        await ctx.response.defer(ephemeral=True)
        
        try:
            count = await self.role_service.sync_roles(ctx.guild)
            logger.info(f"Synced {count} roles for guild {ctx.guild.name}")
            await ctx.edit_original_response(content=f"Синхронизировано **{count}** ролей!")
        except Exception as e:
            logger.error(f"Role service not available for sync_roles command: {e}")
            await ctx.edit_original_response(content=f" Ошибка: {e}")

    @commands.slash_command(name="set_auto_role", description="Установить роль для автовыдачи новичкам")
    async def set_auto_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        role: disnake.Role,
        auto_assign: bool = True
    ):
        """Установить или убрать автовыдачу роли"""
        logger.info(f"set_auto_role command invoked by {ctx.author} for role {role.name}")
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return
        
        if ctx.guild.me.top_role.position <= role.position:
            await ctx.response.send_message("Не могу управлять этой ролью (она выше моей)", ephemeral=True)
            return
        
        await self.role_service.set_auto_assign(role.id, auto_assign)
        
        status = "включена" if auto_assign else "выключена"
        logger.info(f"Auto-assign for role {role.name} set to {auto_assign}")
        await ctx.response.send_message(f"Автовыдача роли **{role.name}** {status}", ephemeral=True)

    @commands.slash_command(name="list_roles", description="Показать все роли сервера")
    async def list_roles(self, ctx: disnake.ApplicationCommandInteraction):
        """Показать список всех ролей"""
        logger.info(f"list_roles command invoked by {ctx.author}")

        roles = await self.role_service.get_all_roles()
        
        if not roles:
            await ctx.response.send_message("Роли не найдены. Используйте `/sync_roles` для синхронизации.")
            return
        
        embed = disnake.Embed(
            title="Список ролей сервера",
            color=disnake.Color.blue()
        )
        
        auto_roles = []
        public_roles = []
        
        for role in roles:
            role_mention = f"<@&{role['role_id']}>"
            if role['is_auto_assign']:
                auto_roles.append(f"• {role_mention} (автовыдача)")
            else:
                public_roles.append(f"• {role_mention}")
        
        if auto_roles:
            embed.add_field(name="Автовыдача", value="\n".join(auto_roles[:10]), inline=False)
        if public_roles:
            embed.add_field(name="Обычные роли", value="\n".join(public_roles[:15]), inline=False)
        
        embed.set_footer(text=f"Всего ролей: {len(roles)}")
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="role_panel", description="Создать панель для выдачи ролей")
    async def role_panel(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        use_pagination: bool = False
    ):
        """Создать embed с кнопками для выдачи ролей"""
        logger.info(f"role_panel command invoked by {ctx.author} in channel #{channel.name}")
        
        if not ctx.author.guild_permissions.administrator:
            logger.warning(f"User {ctx.author} tried to use role_panel without permissions")
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return
        
        public_roles = await self._role_service.get_public_roles()
        
        if not public_roles:
            logger.warning(f"No public roles found for guild {ctx.guild.name}")
            await ctx.response.send_message("Нет публичных ролей для отображения", ephemeral=True)
            return
        
        logger.info(f"Found {len(public_roles)} public roles")
        
        embed = disnake.Embed(
            title="Выберите свою роль",
            description="Нажмите на кнопку, чтобы получить или снять роль",
            color=disnake.Color.green()
        )
        
        role_list = []
        for role in public_roles:
            emoji = role.get('display_emoji', '🎭')
            role_list.append(f"{emoji} <@&{role['role_id']}>")
        
        embed.add_field(
            name="Доступные роли",
            value="\n".join(role_list[:20]),
            inline=False
        )
        embed.set_footer(text="Нажмите на кнопку ниже, чтобы получить роль")
        
        if use_pagination and len(public_roles) > 10:
            logger.info(f"Creating paginated view with {len(public_roles)} roles")
            view = RolePanelPaginatedView(public_roles, items_per_page=10)
        else:
            logger.info(f"Creating simple view with {len(public_roles)} roles")
            view = RolePanelView(public_roles)
        
        await channel.send(embed=embed, view=view)
        logger.info(f"Role panel sent to channel #{channel.name}")
        await ctx.response.send_message(f"Панель ролей создана в канале {channel.mention}", ephemeral=True)

def setup(bot: commands.Bot):
    """Установка кога (для классической загрузки)"""
    pass
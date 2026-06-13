import disnake
from disnake.ext import commands, tasks
from datetime import datetime

from application.services.role_service import RoleService
from infrastructure.logging import get_logger
from presentation.views.role_panel_view import RolePanelView
from presentation.views import (
    CreatePanelRoleSelectView,
    PanelSelectView,
    PanelAddRoleView,
    PanelRemoveRoleView,
    DeletePanelConfirmView,
)

logger = get_logger(__name__)

class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, role_service: RoleService):
        self._bot = bot
        self._role_service = role_service
        logger.info("RolesCog initialized")

    def cog_load(self):
        self.refresh_panels.start()
        logger.info("Started panel refresh task")

    def cog_unload(self):
        self.refresh_panels.cancel()
        logger.info("Stopped panel refresh task")

    @tasks.loop(minutes=5)
    async def refresh_panels(self):
        logger.info("Running scheduled panel refresh")
        try:
            if not self._role_service._panel_message_repo:
                return
            for guild in self._bot.guilds:
                panels = await self._role_service._panel_message_repo.get_by_guild(guild.id)
                for panel in panels:
                    channel = guild.get_channel(panel["channel_id"])
                    if channel:
                        await self._role_service.refresh_panel_view(panel["message_id"], channel)
        except Exception as e:
            logger.error(f"Failed to refresh panels: {e}")

    @refresh_panels.before_loop
    async def before_refresh(self):
        await self._bot.wait_until_ready()

    @property
    def role_service(self):
        return self._role_service

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        logger.info(f"New member joined: {member}")
        assigned = await self.role_service.assign_auto_roles(member)
        if assigned:
            role_names = ", ".join([r.name for r in assigned])
            logger.info(f"Assigned roles {role_names} to {member}")

    @commands.slash_command(name="sync_roles", description="Синхронизировать роли с Discord")
    async def sync_roles(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        await ctx.response.defer(ephemeral=True)
        try:
            count = await self.role_service.sync_roles(ctx.guild)
            logger.info(f"Synced {count} roles for guild {ctx.guild.name}")
            embed = disnake.Embed(
                title="✅ Синхронизация завершена",
                description=f"Синхронизировано **{count}** ролей с базой данных",
                color=disnake.Color.green(),
            )
            await ctx.edit_original_response(embed=embed)
        except Exception as e:
            logger.error(f"sync_roles error: {e}")
            await ctx.edit_original_response(content=f"Ошибка: {e}")

    @commands.slash_command(name="set_auto_role", description="Установить роль для автовыдачи новичкам")
    async def set_auto_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        role: disnake.Role,
        auto_assign: bool = True,
    ):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
            return

        if ctx.guild.me.top_role.position <= role.position:
            await ctx.response.send_message(
                "Не могу управлять этой ролью — она выше моей в иерархии", ephemeral=True
            )
            return

        await self.role_service.set_auto_assign(role.id, auto_assign)
        status = "включена" if auto_assign else "выключена ❌"
        embed = disnake.Embed(
            title="Автовыдача обновлена",
            description=f"Роль {role.mention}: автовыдача {status}",
            color=disnake.Color.green() if auto_assign else disnake.Color.orange(),
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="list_roles", description="Показать все роли сервера")
    async def list_roles(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        roles = await self.role_service.get_all_roles()
        if not roles:
            await ctx.response.send_message(
                "Роли не найдены. Используйте `/sync_roles`.", ephemeral=True
            )
            return

        embed = disnake.Embed(
            title="Роли сервера",
            color=0x5865F2,
        )

        auto_lines, public_lines, hidden_lines = [], [], []
        for r in roles:
            mention = f"<@&{r['role_id']}>"
            emoji_icon = r.get("display_emoji") or ""
            if r["is_auto_assign"]:
                auto_lines.append(f"{emoji_icon} {mention}")
            elif r["is_public"]:
                public_lines.append(f"{emoji_icon} {mention}")
            else:
                hidden_lines.append(f"{emoji_icon} {mention}")

        if auto_lines:
            embed.add_field(name="Автовыдача", value="\n".join(auto_lines[:10]), inline=False)
        if public_lines:
            embed.add_field(name="Публичные", value="\n".join(public_lines[:15]), inline=False)
        if hidden_lines:
            embed.add_field(name="Скрытые (не появятся в панелях)", value="\n".join(hidden_lines[:15]), inline=False)

        embed.set_footer(text=f"Всего ролей: {len(roles)} | публичная · скрытая · автовыдача")
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="set_role_public",
        description="Изменить публичность роли (скрытые роли не попадают в панели)",
    )
    async def set_role_public(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        role: disnake.Role,
        is_public: bool,
    ):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        success = await self.role_service.set_role_public(role.id, is_public)
        if not success:
            await ctx.response.send_message(
                "Роль не найдена в БД. Выполните `/sync_roles` сначала.", ephemeral=True
            )
            return

        status = "публичная 🟢" if is_public else "скрытая 🔴"
        embed = disnake.Embed(
            title="Публичность обновлена",
            description=f"Роль {role.mention} теперь **{status}**",
            color=disnake.Color.green() if is_public else disnake.Color.red(),
        )
        if not is_public:
            embed.set_footer(text="Эта роль больше не будет появляться в панелях ролей")
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="create_panel", description="Создать панель ролей с кнопками")
    async def create_panel(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        title: str = "Выберите свою роль",
        description: str = "Нажмите на кнопку ниже, чтобы получить или снять роль",
    ):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        # Фильтруем только публичные роли, доступные боту
        all_public = await self._role_service.get_public_roles()
        available = []
        for rd in all_public:
            role = ctx.guild.get_role(rd["role_id"])
            if not role:
                continue
            if role.permissions.administrator:
                continue
            if role.managed:
                continue
            if ctx.guild.me.top_role.position <= role.position:
                continue
            available.append(rd)

        if not available:
            await ctx.response.send_message(
                "Нет доступных публичных ролей.\n"
                "• Сначала выполните `/sync_roles`\n"
                "• Убедитесь, что роли помечены публичными через `/set_role_public`",
                ephemeral=True,
            )
            return

        view = CreatePanelRoleSelectView(
            role_service=self._role_service,
            guild=ctx.guild,
            available_roles=available,
            target_channel=channel,
            embed_title=title,
            embed_description=description,
            created_by=ctx.author.id,
        )

        embed = disnake.Embed(
            title="Создание панели ролей",
            description=(
                f"**Канал:** {channel.mention}\n"
                f"**Название:** {title}\n\n"
                "Выберите роли, которые будут отображаться в панели.\n"
                "Для каждой роли можно задать эмодзи (опционально)."
            ),
            color=0x5865F2,
        )
        embed.set_footer(text="После выбора нажмите «Создать панель»")
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.slash_command(name="panel_add", description="Добавить роль в существующую панель")
    async def panel_add(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        panels = await self._role_service._panel_message_repo.get_by_guild(ctx.guild.id)
        if not panels:
            await ctx.response.send_message("На сервере нет созданных панелей", ephemeral=True)
            return

        embed = disnake.Embed(
            title="➕  Добавить роль в панель",
            description="Выберите панель, в которую хотите добавить роль",
            color=0x57F287,
        )
        view = PanelSelectView(
            panels=panels,
            guild=ctx.guild,
            role_service=self._role_service,
            action="add",
        )
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.slash_command(name="panel_remove", description="Удалить роль из существующей панели")
    async def panel_remove(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        panels = await self._role_service._panel_message_repo.get_by_guild(ctx.guild.id)
        if not panels:
            await ctx.response.send_message("На сервере нет созданных панелей", ephemeral=True)
            return

        embed = disnake.Embed(
            title="➖  Удалить роль из панели",
            description="Выберите панель, из которой хотите удалить роль",
            color=0xED4245,
        )
        view = PanelSelectView(
            panels=panels,
            guild=ctx.guild,
            role_service=self._role_service,
            action="remove",
        )
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.slash_command(name="panel_list", description="Показать все панели на сервере")
    async def panel_list(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        panels = await self._role_service._panel_message_repo.get_by_guild(ctx.guild.id)
        if not panels:
            embed = disnake.Embed(
                title="Панели ролей",
                description="На этом сервере ещё нет созданных панелей.\nИспользуйте `/create_panel`",
                color=disnake.Color.light_grey(),
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return

        embed = disnake.Embed(
            title="Панели ролей сервера",
            color=0x5865F2,
        )
        embed.description = f"Всего панелей: **{len(panels)}**"

        for i, panel in enumerate(panels, 1):
            channel = ctx.guild.get_channel(panel["channel_id"])
            channel_info = channel.mention if channel else f"*(канал удалён)*"

            buttons = await self._role_service.get_panel_buttons(panel["message_id"])
            btn_count = len(buttons)

            created_at = panel.get("created_at", "")
            ts_str = ""
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    else:
                        dt = created_at
                    ts_str = f"\nСоздана: <t:{int(dt.timestamp())}:R>"
                except Exception:
                    pass

            msg_link = (
                f"https://discord.com/channels/{ctx.guild.id}/{panel['channel_id']}/{panel['message_id']}"
                if channel
                else ""
            )
            link_text = f"\n🔗 [Перейти к сообщению]({msg_link})" if msg_link else ""

            role_preview = ""
            if buttons:
                previews = []
                for b in buttons[:5]:
                    emoji = b.get("emoji") or "🔘"
                    previews.append(f"{emoji} <@&{b['role_id']}>")
                if len(buttons) > 5:
                    previews.append(f"*...и ещё {len(buttons) - 5}*")
                role_preview = "\n" + "\n".join(previews)

            embed.add_field(
                name=f"{'─' * 24}",
                value=(
                    f"**{i}. {panel.get('embed_title', 'Панель')}**\n"
                    f"Канал: {channel_info}\n"
                    f"`{panel['message_id']}`\n"
                    f"Ролей: **{btn_count}**"
                    f"{ts_str}"
                    f"{link_text}"
                    f"{role_preview}"
                ),
                inline=False,
            )

        embed.set_footer(text="Используйте /panel_add, /panel_remove, /delete_panel для управления")
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="delete_panel", description="Удалить панель ролей")
    async def delete_panel(self, ctx: disnake.ApplicationCommandInteraction):
        if not ctx.author.guild_permissions.administrator:
            await ctx.response.send_message("Только администраторы", ephemeral=True)
            return

        panels = await self._role_service._panel_message_repo.get_by_guild(ctx.guild.id)
        if not panels:
            await ctx.response.send_message("На сервере нет созданных панелей", ephemeral=True)
            return

        embed = disnake.Embed(
            title="🗑️  Удалить панель",
            description="Выберите панель для удаления.\n⚠️ Это действие **необратимо** — сообщение и все кнопки будут удалены.",
            color=0xED4245,
        )
        view = PanelSelectView(
            panels=panels,
            guild=ctx.guild,
            role_service=self._role_service,
            action="delete",
        )
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)


def setup(bot: commands.Bot):
    pass
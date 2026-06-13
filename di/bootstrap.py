import asyncio
import signal
import sys
import disnake
from disnake.ext import commands

from di import Container
from presentation import DiscordBot
from infrastructure.logging.logger import get_logger  # ← исправлен импорт

logger = get_logger(__name__)


class Bootstrap:
    def __init__(self):
        self.container = Container()
        self.bot: DiscordBot = None

    async def run(self):
        """Запуск бота"""
        try:
            role_service = await self.container.get_role_service()
            
            # Создаём бота
            self.bot = DiscordBot(
                config=self.container.config,
                role_service=role_service
            )
            
            # Регистрируем команды
            await self._register_commands()
            
            # Настраиваем обработку сигналов
            self._setup_signal_handlers()
            
            # Запускаем
            token = self.container.config.discord_token.get_secret_value()
            logger.info("Starting bot...")
            await self.bot.start(token)
            
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Shutting down...")
            await self._shutdown()
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self._shutdown()
            sys.exit(1)
    
    def _setup_signal_handlers(self):
        """Настройка обработки сигналов для graceful shutdown"""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self._shutdown())
                )
            except NotImplementedError:
                pass
    
    async def _register_commands(self):
        """Регистрация команд"""
        logger.info("Registering commands...")
        
        @self.bot.slash_command(name="ping", description="Проверка бота")
        async def ping(ctx: disnake.ApplicationCommandInteraction):
            latency = round(self.bot.latency * 1000)
            logger.info(f"Ping command invoked. Latency: {latency}ms")
            await ctx.response.send_message(f"Pong! {latency}ms")
        
        @self.bot.slash_command(name="sync_roles", description="Синхронизировать роли")
        async def sync_roles(ctx: disnake.ApplicationCommandInteraction):
            if not ctx.author.guild_permissions.administrator:
                await ctx.response.send_message("Только администраторы могут использовать эту команду", ephemeral=True)
                return
            
            if not self.bot._role_service:
                logger.error("Role service not available for sync_roles command")
                await ctx.response.send_message("Сервис ролей не доступен", ephemeral=True)
                return
            
            await ctx.response.defer(ephemeral=True)
            
            try:
                guild = ctx.guild
                count = await self.bot._role_service.sync_roles(guild)
                logger.info(f"Sync roles command invoked. {count} roles synchronized for guild {guild.name}")
                await ctx.edit_original_response(content=f"✅ Синхронизировано **{count}** ролей!")
                
                roles = await self.bot._role_service.get_all_roles()
                if roles:
                    role_names = [r['name'] for r in roles[:10]]
                    preview = ', '.join(role_names)
                    if len(roles) > 10:
                        preview += f" и ещё {len(roles) - 10}..."
                    await ctx.followup.send(f"Роли в БД: {preview}", ephemeral=True)

            except Exception as e:
                logger.error(f"Sync roles error: {e}", exc_info=True)
                await ctx.edit_original_response(content=f"❌ Ошибка: {e}")
    
    async def _shutdown(self):
        """Остановка"""
        logger.info("Shutting down...")
        if self.container:
            await self.container.shutdown()
        if self.bot:
            await self.bot.close()
        logger.info("Shutdown complete")
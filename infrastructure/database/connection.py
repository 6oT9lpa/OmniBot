import sqlite3
from pathlib import Path
from typing import Optional
import aiosqlite

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str):
        if database_url.startswith("sqlite:///"):
           self.db_path = database_url[10:]
        else:
            self.db_path = database_url

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._connection: Optional[aiosqlite.Connection] = None
        logger.info(f"Database path: {self.db_path}")

    async def initialize(self) -> None:
        await self.connect()
        await self.enable_wal_mode()
        await self.create_tables()

        logger.info("Database initialized successfully")

    async def connect(self) -> aiosqlite.Connection:
        if not self._connection:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row

            await self._connection.execute("SELECT datetime('now', 'localtime')")

            logger.info("Database connection established")

        return self._connection
    
    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    async def enable_wal_mode(self) -> None:
        if not self._connection:
            await self.connect()
        
        async with self._connection.execute("PRAGMA journal_mode=WAL") as cursor:
            result = await cursor.fetchone()
            logger.info(f"Journal mode: {result[0] if result else 'unknown'}")
    
    async def create_tables(self) -> None:
        await self._create_messages_table()
        await self._create_punishments_table()
        await self._create_streamers_table()
        await self._create_server_stats_table()
        await self._create_roles_table()
        await self._create_channel_config_table()
        await self._create_user_stats_table()
        await self._create_role_panel_messages_table()
        await self._create_role_panel_buttons_table()
        await self._create_server_channel_purposes_table()
        await self._create_welcome_config_table()

        logger.info("All tables created successfully")
    
    async def _create_messages_table(self) -> None:
        """Таблица сообщений"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                content TEXT,
                deleted BOOLEAN DEFAULT 0,
                edited BOOLEAN DEFAULT 0,
                edited_content TEXT,
                ai_flagged BOOLEAN DEFAULT 0,
                ai_reason TEXT,
                timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_author 
            ON messages(author_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_channel 
            ON messages(channel_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_deleted 
            ON messages(deleted)
        """)

        logger.info("Created messages table")

    async def _create_punishments_table(self) -> None:
        """Таблица наказаний"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mod_id INTEGER,
                type TEXT NOT NULL,
                reason TEXT,
                duration TEXT,
                expires_at TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_punishments_user 
            ON punishments(user_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_punishments_active 
            ON punishments(active)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_punishments_expires 
            ON punishments(expires_at)
        """)

        logger.info("Created punishments table")

    async def _create_streamers_table(self) -> None:
        """Таблица стримеров"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS streamers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL CHECK(platform IN ('twitch', 'youtube', 'kick')),
                channel_url TEXT NOT NULL,
                channel_name TEXT,
                template TEXT,
                ping_role_id INTEGER,
                active BOOLEAN DEFAULT 1,
                last_stream_id TEXT,
                last_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, platform)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_streamers_user 
            ON streamers(user_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_streamers_platform 
            ON streamers(platform)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_streamers_active 
            ON streamers(active)
        """)

        logger.info("Created streamers table")

    async def _create_server_stats_table(self) -> None:
        """Таблица статистики сервера"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS server_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                members_total INTEGER DEFAULT 0,
                members_online INTEGER DEFAULT 0,
                members_voice INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                voice_hours REAL DEFAULT 0,
                new_members INTEGER DEFAULT 0,
                left_members INTEGER DEFAULT 0,
                top_channel_id INTEGER,
                top_channel_count INTEGER
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_date 
            ON server_stats(date)
        """)

        logger.info("Created server_stats table")

    async def _create_roles_table(self) -> None:
        """Таблица ролей"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color INTEGER,
                position INTEGER,
                is_auto_assign BOOLEAN DEFAULT 0,
                is_public BOOLEAN DEFAULT 1,
                display_emoji TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_roles_guild 
            ON roles(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_roles_auto_assign 
            ON roles(is_auto_assign)
        """)

        logger.info("Created roles table")

    async def _create_channel_config_table(self) -> None:
        """Таблица конфигурации каналов"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS channel_config (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                is_ai_whitelisted BOOLEAN DEFAULT 0,
                welcome_enabled BOOLEAN DEFAULT 1,
                slowmode_override INTEGER DEFAULT NULL,
                auto_delete_after INTEGER,
                custom_name TEXT,
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_guild 
            ON channel_config(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_whitelist 
            ON channel_config(is_ai_whitelisted)
        """)

        logger.info("Created channel_config table")

    async def _create_user_stats_table(self) -> None:
        """Таблица статистики пользователей"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                messages_count INTEGER DEFAULT 0,
                voice_minutes INTEGER DEFAULT 0,
                warnings_count INTEGER DEFAULT 0,
                last_message TIMESTAMP,
                joined_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_stats_messages 
            ON user_stats(messages_count DESC)
        """)
        logger.info("Created user_stats table")

    async def _create_role_panel_messages_table(self) -> None:
        """Таблица панелей ролей"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS role_panel_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                embed_title TEXT DEFAULT 'Выберите свою роль',
                embed_description TEXT DEFAULT 'Нажмите на кнопку, чтобы получить или снять роль',
                embed_color INTEGER DEFAULT 65280,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(guild_id, channel_id, message_id)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_role_panel_messages_guild 
            ON role_panel_messages(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_role_panel_messages_active 
            ON role_panel_messages(is_active)
        """)
        logger.info("Created role_panel_messages table")

    async def _create_role_panel_buttons_table(self) -> None:
        """Таблица кнопок панелей ролей"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS role_panel_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                panel_message_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                role_name TEXT NOT NULL,
                emoji TEXT,
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (panel_message_id) REFERENCES role_panel_messages(id) ON DELETE CASCADE,
                UNIQUE(panel_message_id, role_id)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_role_panel_buttons_panel 
            ON role_panel_buttons(panel_message_id)
        """)
        logger.info("Created role_panel_buttons table")
    
    async def _create_server_channel_purposes_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS server_channel_purposes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                purpose     TEXT    NOT NULL,
                channel_id  INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at  TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(guild_id, purpose)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_scp_guild
            ON server_channel_purposes(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_scp_purpose
            ON server_channel_purposes(guild_id, purpose)
        """)

    async def _create_welcome_config_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id INTEGER PRIMARY KEY,
                title TEXT DEFAULT 'Добро пожаловать!',
                description TEXT,
                thumbnail_url TEXT,
                footer_text TEXT,
                footer_icon_url TEXT,
                color INTEGER DEFAULT 5763719,
                is_enabled INTEGER DEFAULT 1,
                rules_channel_id INTEGER,
                roles_channel_id INTEGER,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        logger.info("Created welcome_config table")

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Выполнение запроса"""
        conn = await self.connect()
        return await conn.execute(query, params)
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        conn = await self.connect()
        async with conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Получение всех строк"""
        conn = await self.connect()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def commit(self) -> None:
        """Фиксация транзакции"""
        if self._connection:
            await self._connection.commit()
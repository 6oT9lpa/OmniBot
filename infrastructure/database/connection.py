import asyncio
import sqlite3
from pathlib import Path
from typing import Optional

import aiosqlite

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(
        self,
        database_url: str,
        *,
        retry_attempts: int = 8,
        retry_base_delay: float = 0.1,
        sqlite_timeout_seconds: float = 30.0,
    ):
        if database_url.startswith("sqlite:///"):
            self.db_path = database_url[10:]
        else:
            self.db_path = database_url

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.database_url = database_url
        self.retry_attempts = retry_attempts
        self.retry_base_delay = retry_base_delay
        self.sqlite_timeout_seconds = sqlite_timeout_seconds
        self._connection: Optional[aiosqlite.Connection] = None
        logger.info(f"Database path: {self.db_path}")

    async def initialize(self) -> None:
        await self.connect()
        #await self.run_migrations()
        await self.enable_wal_mode()
        await self.create_tables()

        logger.info("Database initialized successfully")

    async def connect(self) -> aiosqlite.Connection:
        if not self._connection:
            self._connection = await aiosqlite.connect(
                self.db_path,
                timeout=self.sqlite_timeout_seconds,
            )
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys=ON")
            await self._connection.execute(
                f"PRAGMA busy_timeout={int(self.sqlite_timeout_seconds * 1000)}"
            )
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

    async def run_migrations(self) -> None:
        alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
        if not alembic_ini.exists():
            logger.warning("Alembic config not found, skipping migrations")
            return

        try:
            from alembic import command
            from alembic.config import Config as AlembicConfig

            config = AlembicConfig(str(alembic_ini))
            config.set_main_option("sqlalchemy.url", self.database_url)
            command.upgrade(config, "head")
            logger.info("Database migrations applied")
        except Exception as exc:
            logger.error(f"Failed to apply database migrations: {exc}", exc_info=True)
            raise

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        async def _execute() -> aiosqlite.Cursor:
            conn = await self.connect()
            return await conn.execute(query, params)

        return await self._with_retry(_execute)

    async def executemany(self, query: str, values_list: list[tuple]) -> aiosqlite.Cursor:
        async def _executemany() -> aiosqlite.Cursor:
            conn = await self.connect()
            return await conn.executemany(query, values_list)

        return await self._with_retry(_executemany)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        async def _fetch_one() -> Optional[dict]:
            conn = await self.connect()
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

        return await self._with_retry(_fetch_one)

    async def fetch_all(self, query: str, params: tuple = ()) -> list:
        async def _fetch_all() -> list:
            conn = await self.connect()
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        return await self._with_retry(_fetch_all)

    async def commit(self) -> None:
        async def _commit() -> None:
            if self._connection:
                await self._connection.commit()

        await self._with_retry(_commit)

    async def cleanup_retention(
        self,
        *,
        message_retention_days: int,
        punishment_retention_days: int,
    ) -> dict[str, int]:
        messages_query = """
            DELETE FROM messages
            WHERE timestamp < datetime('now', 'localtime', ?)
        """
        punishments_query = """
            DELETE FROM punishments
            WHERE active = 0
              AND expires_at IS NOT NULL
              AND expires_at < datetime('now', 'localtime', ?)
        """

        deleted_messages = 0
        deleted_punishments = 0

        try:
            message_cursor = await self.execute(
                messages_query,
                (f"-{message_retention_days} days",),
            )
            deleted_messages = message_cursor.rowcount or 0
            await self.commit()
        except Exception as exc:
            logger.error(f"Failed to cleanup expired messages: {exc}", exc_info=True)

        try:
            punishment_cursor = await self.execute(
                punishments_query,
                (f"-{punishment_retention_days} days",),
            )
            deleted_punishments = punishment_cursor.rowcount or 0
            await self.commit()
        except Exception as exc:
            logger.error(f"Failed to cleanup expired punishments: {exc}", exc_info=True)

        return {
            "messages": deleted_messages,
            "punishments": deleted_punishments,
        }

    async def _with_retry(self, operation):
        delay = self.retry_base_delay
        last_exc: Optional[BaseException] = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                return await operation()
            except aiosqlite.OperationalError as exc:
                last_exc = exc
                message = str(exc).lower()
                if "database is locked" not in message and "database is busy" not in message:
                    raise
                if attempt >= self.retry_attempts:
                    break
                logger.warning(
                    "SQLite database is locked, retrying in %.2fs (attempt %s/%s)",
                    delay,
                    attempt,
                    self.retry_attempts,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 5.0)

        if last_exc:
            raise last_exc
        raise sqlite3.OperationalError("database operation failed")

    async def create_tables(self) -> None:
        await self._create_messages_table()
        await self._create_punishments_table()
        await self._create_streamers_table()
        await self._ensure_streamer_columns()
        await self._create_server_stats_table()
        await self._create_roles_table()
        await self._create_channel_config_table()
        await self._create_user_stats_table()
        await self._create_role_panel_messages_table()
        await self._create_role_panel_buttons_table()
        await self._create_message_logs_table()
        await self._create_guild_event_logs_table()
        await self._ensure_punishment_columns()
        await self._ensure_role_panel_message_columns()
        await self._create_server_channel_purposes_table()
        await self._create_welcome_config_table()
        await self._create_voice_rooms_table()
        await self._ensure_voice_room_columns()
        await self._create_voice_room_members_table()
        await self._create_voice_config_table()
        await self._ensure_messages_columns()
        await self._create_voice_sessions_table()
        await self._create_server_role_purposes_table()
        await self._create_activity_synced_roles_table()
        await self._create_activity_access_roles_table()
        await self._create_activity_access_role_modules_table()
        await self._create_activity_synced_role_assignments_table()
        await self._create_dev_blog_posts_table()

        logger.info("All tables created successfully")

    async def _create_messages_table(self) -> None:
        """Таблица сообщений"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
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
            CREATE INDEX IF NOT EXISTS idx_messages_user 
            ON messages(user_id)
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
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_guild_time 
            ON messages(guild_id, timestamp)
        """)
        await self._connection.commit()

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
        await self._connection.commit()

        logger.info("Created punishments table")

    async def _create_streamers_table(self) -> None:
        """Таблица стримеров"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS streamers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL DEFAULT 0,
                platform TEXT NOT NULL CHECK(platform IN ('twitch', 'youtube', 'kick')),
                channel_url TEXT NOT NULL,
                channel_name TEXT,
                template TEXT,
                ping_role_id INTEGER,
                active BOOLEAN DEFAULT 1,
                last_stream_id TEXT,
                last_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, guild_id, platform)
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
        await self._connection.commit()

        logger.info("Created streamers table")

    async def _ensure_streamer_columns(self) -> None:
        if not await self._column_exists("streamers", "guild_id"):
            await self._connection.execute("ALTER TABLE streamers ADD COLUMN guild_id INTEGER NOT NULL DEFAULT 0")
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_streamers_guild
            ON streamers(guild_id)
        """)
        await self.commit()

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
        await self._connection.commit()

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
        await self._connection.commit()

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
        await self._connection.commit()

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
                last_message TEXT,
                joined_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, guild_id)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_stats_messages
            ON user_stats(messages_count DESC)
        """)
        await self._connection.commit()

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
                interaction_mode TEXT NOT NULL DEFAULT 'buttons',
                view_fingerprint TEXT,
                last_rendered_fingerprint TEXT,
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
        await self._connection.commit()

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
        await self._connection.commit()

        logger.info("Created role_panel_buttons table")

    async def _create_message_logs_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT,
                event_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                retention_until TIMESTAMP
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_logs_guild
            ON message_logs(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_logs_event
            ON message_logs(event_type)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_logs_retention
            ON message_logs(retention_until)
        """)    
        await self._connection.commit()

        logger.info("Created message_logs table")

    async def _create_guild_event_logs_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS guild_event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER,
                actor_id INTEGER,
                actor_name TEXT,
                target_id INTEGER,
                target_name TEXT,
                event_type TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                retention_until TIMESTAMP
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_guild_event_logs_guild
            ON guild_event_logs(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_guild_event_logs_event
            ON guild_event_logs(event_type)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_guild_event_logs_retention
            ON guild_event_logs(retention_until)
        """)
        await self._connection.commit()

        logger.info("Created guild_event_logs table")

    async def _ensure_punishment_columns(self) -> None:
        for column in (
            "guild_id",
            "moderator_id",
            "duration_seconds",
            "is_active",
            "created_at",
            "retention_until",
        ):
            if not await self._column_exists("punishments", column):
                await self._connection.execute(f"ALTER TABLE punishments ADD COLUMN {column} TEXT")

    async def _ensure_role_panel_message_columns(self) -> None:
        for column in (
            "interaction_mode",
            "view_fingerprint",
            "last_rendered_fingerprint",
        ):
            if not await self._column_exists("role_panel_messages", column):
                await self._connection.execute(f"ALTER TABLE role_panel_messages ADD COLUMN {column} TEXT")

    async def _ensure_messages_columns(self) -> None:
        columns = ("user_id", "deleted", "edited", "edited_content", "ai_flagged", "ai_reason", "reply_to_message_id")
        for col in columns:
            if not await self._column_exists("messages", col):
                await self._connection.execute(f"ALTER TABLE messages ADD COLUMN {col}")
        await self.commit()

    async def _column_exists(self, table: str, column: str) -> bool:
        async with self._connection.execute(f"PRAGMA table_info({table})") as cursor:
            rows = await cursor.fetchall()
        return any(row[1] == column for row in rows)

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
            ON server_channel_purposes(purpose)
        """)
        await self._connection.commit()

        logger.info("Created server_channel_purposes table")

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
        await self._connection.commit()

        logger.info("Created welcome_config table")

    async def _create_voice_rooms_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS voice_rooms (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                admin_id INTEGER,
                name TEXT NOT NULL,
                is_persistent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_voice_rooms_guild ON voice_rooms(guild_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_voice_rooms_owner ON voice_rooms(owner_id)")
        await self._connection.commit()
        logger.info("Created voice_rooms table")

    async def _ensure_voice_room_columns(self) -> None:
        if not await self._column_exists("voice_rooms", "admin_id"):
            await self._connection.execute("ALTER TABLE voice_rooms ADD COLUMN admin_id INTEGER")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_voice_rooms_admin ON voice_rooms(admin_id)")
        await self.commit()
        logger.info("Ensured voice_rooms admin columns")

    async def _create_voice_room_members_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS voice_room_members (
                channel_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (channel_id, user_id)
            )
        """)
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_voice_room_members_guild ON voice_room_members(guild_id)"
        )
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_voice_room_members_user ON voice_room_members(user_id)"
        )
        await self.commit()
        logger.info("Created voice_room_members table")

    async def _create_voice_config_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS voice_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await self._connection.commit()
        logger.info("Created voice_config table")

    async def _create_voice_sessions_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS voice_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                joined_at TIMESTAMP NOT NULL,
                left_at TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0
            )
        """)
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_vs_guild ON voice_sessions(guild_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_vs_user ON voice_sessions(user_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_vs_channel ON voice_sessions(channel_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_vs_left ON voice_sessions(left_at)")
        await self.commit()
        logger.info("Created voice_sessions table")

    async def _create_server_role_purposes_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS server_role_purposes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(guild_id, purpose)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_srp_guild
            ON server_role_purposes(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_srp_purpose
            ON server_role_purposes(purpose)
        """)
        await self.commit()
        logger.info("Created server_role_purposes table")

    async def _create_activity_synced_roles_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS activity_synced_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0,
                permissions INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                managed BOOLEAN DEFAULT 0,
                mentionable BOOLEAN DEFAULT 0,
                synced_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(guild_id, role_id)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_synced_roles_guild
            ON activity_synced_roles(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_synced_roles_admin
            ON activity_synced_roles(guild_id, is_admin)
        """)
        await self.commit()
        logger.info("Created activity_synced_roles table")

    async def _create_activity_access_roles_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS activity_access_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                slug TEXT NOT NULL,
                name TEXT NOT NULL,
                is_builtin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(guild_id, slug),
                UNIQUE(guild_id, name)
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_access_roles_guild
            ON activity_access_roles(guild_id)
        """)
        await self.commit()
        logger.info("Created activity_access_roles table")

    async def _create_activity_access_role_modules_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS activity_access_role_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_role_id INTEGER NOT NULL,
                module_key TEXT NOT NULL,
                permission TEXT NOT NULL,
                UNIQUE(access_role_id, module_key),
                FOREIGN KEY(access_role_id)
                    REFERENCES activity_access_roles(id)
                    ON DELETE CASCADE
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_access_role_modules_role
            ON activity_access_role_modules(access_role_id)
        """)
        await self.commit()
        logger.info("Created activity_access_role_modules table")

    async def _create_activity_synced_role_assignments_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS activity_synced_role_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                discord_role_id INTEGER NOT NULL,
                access_role_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(guild_id, discord_role_id, access_role_id),
                FOREIGN KEY(access_role_id)
                    REFERENCES activity_access_roles(id)
                    ON DELETE CASCADE
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_synced_role_assignments_guild_role
            ON activity_synced_role_assignments(guild_id, discord_role_id)
        """)
        await self.commit()
        logger.info("Created activity_synced_role_assignments table")

    async def _create_dev_blog_posts_table(self) -> None:
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS dev_blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                author_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'published',
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_dev_blog_posts_guild
            ON dev_blog_posts(guild_id)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_dev_blog_posts_author
            ON dev_blog_posts(author_id)
        """)
        await self.commit()
        logger.info("Created dev_blog_posts table")

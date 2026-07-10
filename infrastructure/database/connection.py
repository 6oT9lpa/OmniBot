from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, TypeVar

import psycopg
from psycopg.rows import dict_row

from infrastructure.database.cursor_result import DatabaseCursorResult
from infrastructure.database.postgres_schema import PostgresSchema
from infrastructure.logging import get_logger


logger = get_logger(__name__)
T = TypeVar("T")


class DatabaseManager:
    """PostgreSQL-only asynchronous database connection manager."""

    def __init__(
        self,
        database_url: str,
        *,
        retry_attempts: int = 8,
        retry_base_delay: float = 0.1,
        connect_timeout_seconds: float = 10.0,
    ) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must use the postgresql:// scheme")

        self._database_url = database_url
        self.retry_attempts = max(1, retry_attempts)
        self.retry_base_delay = max(0.01, retry_base_delay)
        self.connect_timeout_seconds = max(1.0, connect_timeout_seconds)
        self._connection: Optional[psycopg.AsyncConnection] = None
        self._connection_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        self._closing = False
        logger.info("PostgreSQL database backend initialized")

    @property
    def database_url(self) -> str:
        return self._database_url

    @property
    def backend_name(self) -> str:
        return "postgresql"

    @property
    def is_postgres(self) -> bool:
        return True

    async def initialize(self) -> None:
        await self.connect()
        await self.create_tables()
        logger.info("PostgreSQL database initialized successfully")

    async def connect(self) -> psycopg.AsyncConnection:
        if self._closing:
            raise RuntimeError("Database manager is closing")
        if self._connection is not None and not self._connection.closed:
            return self._connection

        async with self._connection_lock:
            if self._connection is not None and not self._connection.closed:
                return self._connection

            delay = self.retry_base_delay
            last_error: Optional[BaseException] = None
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    self._connection = await psycopg.AsyncConnection.connect(
                        self._database_url,
                        autocommit=True,
                        row_factory=dict_row,
                        connect_timeout=self.connect_timeout_seconds,
                    )
                    logger.info("PostgreSQL database connection established")
                    return self._connection
                except psycopg.Error as exc:
                    last_error = exc
                    if attempt >= self.retry_attempts:
                        break
                    logger.warning(
                        "PostgreSQL connection failed; retrying in %.2fs (attempt %s/%s, error=%s)",
                        delay,
                        attempt,
                        self.retry_attempts,
                        type(exc).__name__,
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 5.0)

            raise ConnectionError("Unable to connect to PostgreSQL") from last_error

    async def close(self) -> None:
        self._closing = True
        async with self._operation_lock:
            connection = self._connection
            self._connection = None
            if connection is not None and not connection.closed:
                await connection.close()
                logger.info("PostgreSQL database connection closed")

    async def run_migrations(self) -> None:
        alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
        if not alembic_ini.exists():
            raise FileNotFoundError("Alembic configuration is missing")

        from alembic import command
        from alembic.config import Config as AlembicConfig

        config = AlembicConfig(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", self._sqlalchemy_url())
        await asyncio.to_thread(command.upgrade, config, "head")
        logger.info("PostgreSQL database migrations applied")

    async def execute(self, query: str, params: tuple = ()) -> DatabaseCursorResult:
        async def operation() -> DatabaseCursorResult:
            async with self._operation_lock:
                connection = await self.connect()
                async with connection.cursor() as cursor:
                    await cursor.execute(self._prepare_query(query), params)
                    rowcount = cursor.rowcount

                lastrowid: Optional[int] = None
                if query.lstrip().lower().startswith("insert"):
                    try:
                        async with connection.cursor() as cursor:
                            await cursor.execute("SELECT LASTVAL() AS lastrowid")
                            row = await cursor.fetchone()
                            if row and row.get("lastrowid") is not None:
                                lastrowid = int(row["lastrowid"])
                    except psycopg.errors.ObjectNotInPrerequisiteState:
                        lastrowid = None

                return DatabaseCursorResult(rowcount=rowcount, lastrowid=lastrowid)

        return await self._with_retry(operation)

    async def executemany(self, query: str, values_list: list[tuple]) -> DatabaseCursorResult:
        async def operation() -> DatabaseCursorResult:
            async with self._operation_lock:
                connection = await self.connect()
                async with connection.cursor() as cursor:
                    await cursor.executemany(self._prepare_query(query), values_list)
                    return DatabaseCursorResult(rowcount=cursor.rowcount)

        return await self._with_retry(operation)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        async def operation() -> Optional[dict]:
            async with self._operation_lock:
                connection = await self.connect()
                async with connection.cursor() as cursor:
                    await cursor.execute(self._prepare_query(query), params)
                    row = await cursor.fetchone()
                    return dict(row) if row else None

        return await self._with_retry(operation)

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        async def operation() -> list[dict]:
            async with self._operation_lock:
                connection = await self.connect()
                async with connection.cursor() as cursor:
                    await cursor.execute(self._prepare_query(query), params)
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]

        return await self._with_retry(operation)

    async def execute_write(self, query: str, params: tuple = ()) -> dict[str, Optional[int]]:
        result = await self.execute(query, params)
        return {"lastrowid": result.lastrowid, "rowcount": result.rowcount}

    async def commit(self) -> None:
        # Connections use PostgreSQL autocommit. Kept for repository compatibility.
        return None

    async def create_tables(self) -> None:
        for statement in PostgresSchema.statements():
            await self.execute_write(statement)
        logger.info("All PostgreSQL tables created successfully")

    async def cleanup_retention(
        self,
        *,
        message_retention_days: int,
        punishment_retention_days: int,
    ) -> dict[str, int]:
        message_result = await self.execute(
            """
            DELETE FROM messages
            WHERE timestamp < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            """,
            (max(1, message_retention_days),),
        )
        punishment_result = await self.execute(
            """
            DELETE FROM punishments
            WHERE COALESCE(is_active, active, 0) = 0
              AND COALESCE(
                    retention_until,
                    created_at + (%s * INTERVAL '1 day'),
                    expires_at + (%s * INTERVAL '1 day')
                  ) < CURRENT_TIMESTAMP
            """,
            (max(1, punishment_retention_days), max(1, punishment_retention_days)),
        )
        return {
            "messages": message_result.rowcount or 0,
            "punishments": punishment_result.rowcount or 0,
        }

    async def _with_retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        delay = self.retry_base_delay
        last_error: Optional[psycopg.Error] = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                return await operation()
            except psycopg.Error as exc:
                if not self._is_retryable(exc):
                    raise
                last_error = exc
                await self._invalidate_connection_if_broken(exc)
                if attempt >= self.retry_attempts:
                    break
                logger.warning(
                    "PostgreSQL operation retry in %.2fs (attempt %s/%s, error=%s)",
                    delay,
                    attempt,
                    self.retry_attempts,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 5.0)

        if last_error is not None:
            raise last_error
        raise RuntimeError("PostgreSQL operation failed")

    async def _invalidate_connection_if_broken(self, exc: psycopg.Error) -> None:
        sqlstate = exc.sqlstate or ""
        connection = self._connection
        if not sqlstate.startswith("08") and connection is not None and not connection.closed:
            return
        self._connection = None
        if connection is not None and not connection.closed:
            try:
                await connection.close()
            except psycopg.Error:
                pass

    @staticmethod
    def _is_retryable(exc: psycopg.Error) -> bool:
        sqlstate = exc.sqlstate or ""
        return sqlstate.startswith("08") or sqlstate in {"40001", "40P01"}

    @staticmethod
    def _prepare_query(query: str) -> str:
        return query.replace("?", "%s")

    def _sqlalchemy_url(self) -> str:
        if self._database_url.startswith("postgresql://"):
            return self._database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self._database_url.replace("postgres://", "postgresql+psycopg://", 1)

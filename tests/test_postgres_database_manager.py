import os

import pytest
import pytest_asyncio

from infrastructure.database import DatabaseManager


pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_DATABASE_URL"),
    reason="POSTGRES_TEST_DATABASE_URL is not configured",
)


@pytest_asyncio.fixture
async def postgres_db():
    manager = DatabaseManager(os.environ["POSTGRES_TEST_DATABASE_URL"])
    await manager.initialize()
    await manager.execute_write(
        """
        TRUNCATE TABLE
            messages,
            voice_room_members,
            voice_rooms,
            guild_event_logs,
            activity_access_role_modules,
            activity_access_roles
        RESTART IDENTITY CASCADE
        """
    )
    try:
        yield manager
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_postgres_database_manager_creates_runtime_schema(postgres_db):
    tables = await postgres_db.fetch_all(
        "SELECT tablename AS name FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
    )
    names = {row["name"] for row in tables}

    assert "messages" in names
    assert "voice_rooms" in names
    assert "guild_event_logs" in names


@pytest.mark.asyncio
async def test_postgres_database_manager_translates_placeholders_and_lastrowid(postgres_db):
    result = await postgres_db.execute_write(
        """
        INSERT INTO guild_event_logs (guild_id, event_type, details)
        VALUES (?, ?, ?)
        """,
        (115, "postgres_probe", "ok"),
    )
    row = await postgres_db.fetch_one(
        "SELECT id, guild_id, event_type FROM guild_event_logs WHERE id = ?",
        (result["lastrowid"],),
    )

    assert result["lastrowid"] == 1
    assert result["rowcount"] == 1
    assert row == {"id": 1, "guild_id": 115, "event_type": "postgres_probe"}


@pytest.mark.asyncio
async def test_postgres_database_manager_supports_voice_room_upserts(postgres_db):
    await postgres_db.execute_write(
        "INSERT INTO voice_rooms (channel_id, guild_id, owner_id, name) VALUES (?, ?, ?, ?)",
        (700, 115, 42, "voice"),
    )
    await postgres_db.execute_write(
        """
        INSERT INTO voice_room_members (channel_id, guild_id, user_id)
        VALUES (?, ?, ?)
        ON CONFLICT(channel_id, user_id)
        DO UPDATE SET joined_at = CURRENT_TIMESTAMP
        """,
        (700, 115, 42),
    )
    await postgres_db.execute_write(
        """
        INSERT INTO voice_room_members (channel_id, guild_id, user_id)
        VALUES (?, ?, ?)
        ON CONFLICT(channel_id, user_id)
        DO UPDATE SET joined_at = CURRENT_TIMESTAMP
        """,
        (700, 115, 42),
    )

    rows = await postgres_db.fetch_all(
        "SELECT user_id FROM voice_room_members WHERE channel_id = ?",
        (700,),
    )

    assert rows == [{"user_id": 42}]

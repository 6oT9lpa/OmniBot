import pytest

@pytest.mark.asyncio
async def test_database_manager_creates_logging_tables(postgres_test_db):
    tables = await postgres_test_db.fetch_all(
        "SELECT tablename AS name FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
    )
    names = {row["name"] for row in tables}
    assert {"message_logs", "guild_event_logs", "punishments", "voice_room_members", "creator_alert_subscriptions"} <= names


@pytest.mark.asyncio
async def test_database_manager_reports_postgresql_backend(postgres_test_db):
    assert postgres_test_db.backend_name == "postgresql"
    assert postgres_test_db.is_postgres is True


@pytest.mark.asyncio
async def test_database_manager_execute_write_returns_postgresql_metadata(postgres_test_db):
    result = await postgres_test_db.execute_write(
        "INSERT INTO guild_event_logs (guild_id, event_type) VALUES (?, ?)",
        (100, "probe"),
    )
    row = await postgres_test_db.fetch_one(
        "SELECT id, event_type FROM guild_event_logs WHERE id = ?", (result["lastrowid"],)
    )
    assert result["lastrowid"] == 1
    assert result["rowcount"] == 1
    assert row == {"id": 1, "event_type": "probe"}

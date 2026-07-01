import pytest

from infrastructure.database import DatabaseManager


@pytest.mark.asyncio
async def test_database_manager_creates_logging_tables(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        await manager.initialize()
        tables = await manager.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row["name"] for row in tables}
        assert "message_logs" in names
        assert "guild_event_logs" in names
        assert "punishments" in names
        assert "voice_room_members" in names
    finally:
        await manager.close()

@pytest.mark.asyncio
async def test_database_manager_uses_extended_sqlite_busy_timeout(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'busy.db'}")
    try:
        await manager.initialize()
        row = await manager.fetch_one("PRAGMA busy_timeout")
        assert row["timeout"] == 30000
    finally:
        await manager.close()

@pytest.mark.asyncio
async def test_database_manager_execute_write_commits_and_returns_metadata(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'write.db'}")
    try:
        await manager.initialize()
        await manager.execute_write("CREATE TABLE write_probe (id INTEGER PRIMARY KEY, name TEXT)")
        result = await manager.execute_write("INSERT INTO write_probe (name) VALUES (?)", ("voice",))
        row = await manager.fetch_one("SELECT id, name FROM write_probe WHERE id = ?", (result["lastrowid"],))

        assert result["lastrowid"] == 1
        assert result["rowcount"] == 1
        assert row == {"id": 1, "name": "voice"}
    finally:
        await manager.close()

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
    finally:
        await manager.close()

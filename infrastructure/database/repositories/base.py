from __future__ import annotations

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import aiosqlite

from infrastructure.database.connection import DatabaseManager
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class BaseRepository:
    """Базовый репозиторий с общими CRUD операциями"""

    def __init__(self, db_manager: DatabaseManager):
        self._db_manager = db_manager
        self._TABLE_NAME: str = ""

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Выполнить SQL запрос"""
        return await self._db_manager.execute(query, params)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Получить одну запись"""
        return await self._db_manager.fetch_one(query, params)

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Получить все записи"""
        return await self._db_manager.fetch_all(query, params)

    async def commit(self) -> None:
        """Зафиксировать изменения"""
        await self._db_manager.commit()

    async def insert(self, data: Dict[str, Any]) -> bool:
        """Вставить новую запись"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {self._TABLE_NAME} ({columns}) VALUES ({placeholders})"
        try:
            await self.execute(query, tuple(data.values()))
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Insert error: {e}")
            return False

    async def upsert(self, data: Dict[str, Any], conflict_column: str = "id") -> bool:
        """Вставить или обновить запись"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        
        update_parts = []
        for key in data.keys():
            if key != conflict_column:
                update_parts.append(f"{key} = excluded.{key}")
        update_str = ", ".join(update_parts)
        
        query = f"""
            INSERT INTO {self._TABLE_NAME} ({columns}) 
            VALUES ({placeholders})
            ON CONFLICT({conflict_column}) DO UPDATE SET {update_str}
        """
        try:
            await self.execute(query, tuple(data.values()))
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Upsert error: {e}")
            return False

    async def update(self, data: Dict[str, Any], where_column: str, where_value: Any) -> bool:
        """Обновить запись"""
        set_parts = ", ".join(f"{key} = ?" for key in data.keys())
        query = f"UPDATE {self._TABLE_NAME} SET {set_parts} WHERE {where_column} = ?"
        params = tuple(data.values()) + (where_value,)
        try:
            await self.execute(query, params)
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Update error: {e}")
            return False

    async def delete(self, where_column: str, where_value: Any) -> bool:
        """Удалить запись"""
        query = f"DELETE FROM {self._TABLE_NAME} WHERE {where_column} = ?"
        try:
            await self.execute(query, (where_value,))
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return False

    async def exists(self, where_column: str, where_value: Any) -> bool:
        """Проверить существование записи"""
        query = f"SELECT 1 FROM {self._TABLE_NAME} WHERE {where_column} = ? LIMIT 1"
        result = await self.fetch_one(query, (where_value,))
        return result is not None

    async def count(self, where_column: str = None, where_value: Any = None) -> int:
        """Посчитать количество записей"""
        if where_column and where_value is not None:
            query = f"SELECT COUNT(*) as count FROM {self._TABLE_NAME} WHERE {where_column} = ?"
            result = await self.fetch_one(query, (where_value,))
        else:
            query = f"SELECT COUNT(*) as count FROM {self._TABLE_NAME}"
            result = await self.fetch_one(query)
        return result["count"] if result else 0
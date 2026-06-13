from __future__ import annotations

from abc import ABC
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TypeVar,
    Generic,
)

import aiosqlite

from infrastructure.database import DatabaseManager
from infrastructure.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    _TABLE_NAME: str = ""
    _ALLOWED_COLUMNS: set[str] = set()
    _DEFAULT_SORT_COLUMN: str = "id"

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

        if not self._TABLE_NAME:
            raise ValueError(
                f"{self.__class__.__name__}: "
                "_TABLE_NAME is not defined"
            )

        logger.debug(
            f"Repository initialized for table: "
            f"{self._TABLE_NAME}"
        )

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Выполнить запрос и вернуть курсор"""
        return await self.db.execute(query, params)
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Выполнить запрос и вернуть одну запись в виде словаря"""
        return await self.db.fetch_one(query, params)
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Выполнить запрос и вернуть все результаты в виде списка словарей"""
        return await self.db.fetch_all(query, params)   
    
    async def commit(self) -> None:
        """Коммит транзакции"""
        await self.db.commit()

    def _validate_column(self, column: str) -> None:
        if self._ALLOWED_COLUMNS and column not in self._ALLOWED_COLUMNS:
            logger.error(
                f"Invalid column: {column}. ",
                f"Allowed columns: {self._ALLOWED_COLUMNS}"
            )
            raise ValueError(
                f"Invalid column: {column}. "
                f"Allowed columns: {self._ALLOWED_COLUMNS}"
            )

    # CRUD operations
    async def insert(
        self, 
        data: Dict[str, Any]
    ) -> Optional[int]:
        """Вставить одну запись и вернуть ID новой записи (если поддерживается)"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        
        query = f"""
            INSERT INTO {self._TABLE_NAME} ({columns})
            VALUES ({placeholders})
        """

        try:
            cursor = await self.execute(query, values)
            await self.commit()

            if hasattr(cursor, 'lastrowid') and cursor.lastrowid is not None:
                logger.debug(f"Inserted data into {self._TABLE_NAME} with ID: {cursor.lastrowid}")
                return cursor.lastrowid
            
            logger.debug(f"Inserted data into {self._TABLE_NAME}")
            return None
        
        except Exception as e:
            logger.error(f"Error inserting data into {self._TABLE_NAME}: {e}")
            raise

    async def insert_many(
        self, 
        data_list: List[Dict[str, Any]]
    ) -> Optional[int]:
        """Вставить несколько записей за один запрос"""
        if not data_list:
            logger.warning("No data provided for bulk insert")
            return 0
        
        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['?' for _ in data_list[0]])
        values_list = [tuple(data.values()) for data in data_list]
        
        query = f"""
            INSERT INTO {self._TABLE_NAME} ({columns})
            VALUES ({placeholders})
        """

        try:
            cursor = await self.db.executemany(query, values_list)
            await self.commit()
            logger.debug(f"Inserted {len(data_list)} rows into {self._TABLE_NAME}")
            return len(data_list)
        
        except Exception as e:
            logger.error(f"Failed to insert many into {self._TABLE_NAME}: {e}")
            raise

    async def update(
        self,
        data: Dict[str, Any],
        where_column: str,
        where_value: Any
    ) -> bool:
        """Обновить запись по условию"""

        for col in data.keys():
            self._validate_column(col)

        self._validate_column(
            where_column
        )

        set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
        values = tuple(data.values()) + (where_value,)
        
        query = f"""
            UPDATE {self._TABLE_NAME}
            SET {set_clause}
            WHERE {where_column} = ?
        """

        try:
            cursor = await self.execute(query, values)
            await self.commit()
            updated = cursor.rowcount > 0
            if updated:
                logger.debug(f"Updated row in {self._TABLE_NAME} where {where_column} = {where_value}")
            else:
                logger.debug(f"No rows updated in {self._TABLE_NAME} where {where_column} = {where_value}")
            return updated
        
        except Exception as e:
            logger.error(f"Error updating data in {self._TABLE_NAME}: {e}")
            raise
    
    async def delete(
        self,
        where_column: str,
        where_value: Any
    ) -> bool:
        """Удалить запись по условию"""

        self._validate_column(
            where_column
        )

        query = f"""
            DELETE FROM {self._TABLE_NAME}
            WHERE {where_column} = ?
        """

        try:
            cursor = await self.execute(query, (where_value,))
            await self.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug(f"Deleted row from {self._TABLE_NAME} where {where_column} = {where_value}")
            else:
                logger.debug(f"No rows deleted from {self._TABLE_NAME} where {where_column} = {where_value}")

            return deleted
        
        except Exception as e:
            logger.error(f"Error deleting data from {self._TABLE_NAME}: {e}")
            raise
    
    async def get_by_id(
        self,
        record_id: int,
        id_column: str = "id"
    ) -> Optional[Dict[str, Any]]:
        """Получить запись по ID"""

        self._validate_column(
            id_column
        )

        query = f"""
            SELECT * FROM {self._TABLE_NAME}
            WHERE {id_column} = ?
        """
        try:
            result = await self.fetch_one(query, (record_id,))
            if result:
                logger.debug(f"Fetched record from {self._TABLE_NAME} where {id_column} = {record_id}")
            else:
                logger.debug(f"No record found in {self._TABLE_NAME} where {id_column} = {record_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error fetching data from {self._TABLE_NAME}: {e}")
            raise

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = None,
        order_dir: str = "ASC"
    ) -> List[Dict[str, Any]]:
        """Получить все записи с пагинацией"""
        if order_by is None:
            order_by = self._DEFAULT_SORT_COLUMN

        self._validate_column(order_by)

        query = f"""
            SELECT * FROM {self._TABLE_NAME}
            ORDER BY {order_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        try:
            results = await self.fetch_all(query, (limit, offset))
            logger.debug(f"Fetched {len(results)} records from {self._TABLE_NAME}")
            return results
        
        except Exception as e:
            logger.error(f"Error fetching data from {self._TABLE_NAME}: {e}")
            raise

    async def count(
        self,
        where_column: Optional[str] = None,
        param: Optional[Any] = None
    ) -> Optional[int]:
        """Подсчитать количество записей"""
        query = f"SELECT COUNT(*) as count FROM {self._TABLE_NAME}"

        if where_column and param:
            query += f" WHERE {where_column} = ?"
        
        try:
            result = await self.fetch_one(query, param if param else ())
            count = result['count'] if result else 0
            logger.debug(f"Counted {count} records in {self._TABLE_NAME}")
            return count
        
        except Exception as e:
            logger.error(f"Error counting records in {self._TABLE_NAME}: {e}")
            raise

    async def exists(
        self,
        where_column: str,
        where_value: Any
    ) -> Optional[bool]:
        """Проверить существует ли запись"""

        self._validate_column(
            where_column
        )

        query = f"""
            SELECT 1 FROM {self._TABLE_NAME}
            WHERE {where_column} = ?
            LIMIT 1
        """
        try:
            result = await self.fetch_one(query, (where_value,))
            exists = result is not None
            logger.debug(f"Existence check in {self._TABLE_NAME} where {where_column} = {where_value}: {exists}")
            return exists
        
        except Exception as e:
            logger.error(f"Error checking existence in {self._TABLE_NAME}: {e}")
            raise

    async def upsert(
        self,
        data: Dict[str, Any],
        conflict_column: str
    ) -> Optional[int]:
        """Вставить или обновить запись"""
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        set_clause = ', '.join([f"{col} = excluded.{col}" for col in data.keys() if col != conflict_column])
        
        query = f"""
            INSERT INTO {self._TABLE_NAME} ({columns})
            VALUES ({placeholders})
            ON CONFLICT({conflict_column}) DO UPDATE SET
            {set_clause}
        """
        values = tuple(data.values())
        
        try:
            cursor = await self.execute(query, values)
            await self.commit()
            if hasattr(cursor, 'lastrowid') and cursor.lastrowid is not None:
                logger.debug(f"Upserted data into {self._TABLE_NAME} with ID: {cursor.lastrowid}")
                return cursor.lastrowid
            
            logger.debug(f"Upserted data into {self._TABLE_NAME}")
            return None
        
        except Exception as e:
            logger.error(f"Error upserting data into {self._TABLE_NAME}: {e}")
            raise
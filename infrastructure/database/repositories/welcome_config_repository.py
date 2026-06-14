from typing import Optional, Dict, Any

from core.interfaces.repositories import WelcomeConfigRepositoryInterface
from infrastructure.database.connection import DatabaseManager
from infrastructure.database.repositories.base import BaseRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class WelcomeConfigRepository(WelcomeConfigRepositoryInterface, BaseRepository):
    _TABLE_NAME = "welcome_config"
    _ALLOWED_COLUMNS = {
        "guild_id", "title", "description", "thumbnail_url",
        "footer_text", "footer_icon_url", "color", "is_enabled",
        "rules_channel_id", "roles_channel_id", "created_at", "updated_at"
    }

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def get_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetch_one(
            "SELECT * FROM welcome_config WHERE guild_id = ?",
            (guild_id,)
        )

    async def create_or_update(
        self,
        guild_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        color: Optional[int] = None,
        is_enabled: Optional[bool] = None,
        rules_channel_id: Optional[int] = None,
        roles_channel_id: Optional[int] = None,
    ) -> bool:
        try:
            existing = await self.get_config(guild_id)
            logger.debug(f"create_or_update called with: title={title!r}, description={description!r}, color={color}, thumbnail_url={thumbnail_url!r}")
            logger.info(f"Existing config for guild {guild_id}: {existing is not None}")

            if existing:
                update_fields = []
                update_values = []
                
                if title is not None:
                    update_fields.append("title = ?")
                    update_values.append(title)
                if description is not None:
                    update_fields.append("description = ?")
                    update_values.append(description)
                if thumbnail_url is not None:
                    update_fields.append("thumbnail_url = ?")
                    update_values.append(thumbnail_url)
                if footer_text is not None:
                    update_fields.append("footer_text = ?")
                    update_values.append(footer_text)
                if footer_icon_url is not None:
                    update_fields.append("footer_icon_url = ?")
                    update_values.append(footer_icon_url)
                if color is not None:
                    update_fields.append("color = ?")
                    update_values.append(color)
                if is_enabled is not None:
                    update_fields.append("is_enabled = ?")
                    update_values.append(1 if is_enabled else 0)
                if rules_channel_id is not None:
                    update_fields.append("rules_channel_id = ?")
                    update_values.append(rules_channel_id)
                if roles_channel_id is not None:
                    update_fields.append("roles_channel_id = ?")
                    update_values.append(roles_channel_id)
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                if update_fields:
                    query = f"""
                        UPDATE {self._TABLE_NAME}
                        SET {', '.join(update_fields)}
                        WHERE guild_id = ?
                    """
                    update_values.append(guild_id)
                    
                    logger.info(f"Executing UPDATE query for guild {guild_id}")
                    await self.execute(query, tuple(update_values))
                    await self.commit()
                    logger.info(f"Updated welcome config for guild {guild_id}")
                else:
                    logger.debug(f"No fields to update for guild {guild_id}")
            else:
                data = {
                    "guild_id": guild_id,
                    "title": title,
                    "description": description,
                    "thumbnail_url": thumbnail_url,
                    "footer_text": footer_text,
                    "footer_icon_url": footer_icon_url,
                    "color": color,
                    "is_enabled": 1 if is_enabled else 1,
                    "rules_channel_id": rules_channel_id,
                    "roles_channel_id": roles_channel_id,
                }
                
                logger.info(f"Executing INSERT query for guild {guild_id} with data: {data}")
                
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = tuple(data.values())
                
                query = f"""
                    INSERT INTO {self._TABLE_NAME} ({columns})
                    VALUES ({placeholders})
                """
                
                await self.execute(query, values)
                await self.commit()
                logger.info(f"Created welcome config for guild {guild_id}")

            return True
            
        except Exception as e:
            logger.error(f"Error in create_or_update for guild {guild_id}: {e}", exc_info=True)
            return False

    async def set_enabled(self, guild_id: int, is_enabled: bool) -> bool:
        try:
            query = f"""
                UPDATE {self._TABLE_NAME}
                SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """
            await self.execute(query, (1 if is_enabled else 0, guild_id))
            await self.commit()
            logger.info(f"Set enabled={is_enabled} for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting enabled for guild {guild_id}: {e}")
            return False

    async def delete_config(self, guild_id: int) -> bool:
        try:
            query = f"DELETE FROM {self._TABLE_NAME} WHERE guild_id = ?"
            await self.execute(query, (guild_id,))
            await self.commit()
            logger.info(f"Deleted config for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting config for guild {guild_id}: {e}")
            return False
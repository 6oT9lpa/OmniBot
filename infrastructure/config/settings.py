from typing import Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class BotConfig(BaseSettings):
    """Configuration for the bot"""

    # Discord
    discord_token: SecretStr = Field(..., env="DISCORD_TOKEN")
    discord_guild_id: int = Field(..., env="DISCORD_GUILD_ID")
    discord_owner_id: int = Field(..., env="DISCORD_OWNER_ID")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Optional IDs for channels and roles
    auto_role_id: Optional[int] = Field(None, env="AUTO_ROLE_ID")

    log_channel_id: Optional[int] = Field(None, env="LOG_CHANNEL_ID")
    welcome_channel_id: Optional[int] = Field(None, env="WELCOME_CHANNEL_ID")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    # Validators
    @field_validator('discord_guild_id', 'discord_owner_id')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f'ID must be positive: {v}')
        return v
    
    @field_validator('auto_role_id', 'log_channel_id', 'welcome_channel_id', mode='before')
    @classmethod
    def parse_id(cls, v):
        if isinstance(v, str):
            return int(v.strip())
        return v
    
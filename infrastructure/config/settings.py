from typing import Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class BotConfig(BaseSettings):
    # Discord
    discord_token: SecretStr = Field(..., env="DISCORD_TOKEN")
    discord_guild_id: Optional[int] = Field(None, env="DISCORD_GUILD_ID")
    discord_owner_id: int = Field(..., env="DISCORD_OWNER_ID")
    discord_proxy_url: Optional[str] = Field(None, env="DISCORD_PROXY_URL")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Optional IDs for channels and roles
    auto_role_id: Optional[int] = Field(None, env="AUTO_ROLE_ID")

    log_channel_id: Optional[int] = Field(None, env="LOG_CHANNEL_ID")
    welcome_channel_id: Optional[int] = Field(None, env="WELCOME_CHANNEL_ID")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Retention
    message_log_retention_days: int = Field(30, env="MESSAGE_LOG_RETENTION_DAYS")
    punishment_retention_days: int = Field(365, env="PUNISHMENT_RETENTION_DAYS")
    retention_cleanup_interval_hours: int = Field(6, env="RETENTION_CLEANUP_INTERVAL_HOURS")

    command_prefix: str = Field("!", env="COMMAND_PREFIX")
    activity_name: str = Field("Omnibot | центр управления", env="ACTIVITY_NAME")
    bot_status: str = Field("online", env="BOT_STATUS")
    activity_rotation_enabled: bool = Field(True, env="ACTIVITY_ROTATION_ENABLED")
    activity_rotation_interval_seconds: int = Field(600, env="ACTIVITY_ROTATION_INTERVAL_SECONDS")
    presence_activities: str = Field("", env="PRESENCE_ACTIVITIES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    # Validators
    @field_validator('discord_guild_id', 'discord_owner_id')
    @classmethod
    def validate_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v <= 0:
            raise ValueError(f'ID must be positive: {v}')
        return v
    
    @field_validator('discord_guild_id', 'auto_role_id', 'log_channel_id', 'welcome_channel_id', mode='before')
    @classmethod
    def parse_id(cls, v):
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            return int(stripped)
        return v

    @field_validator('activity_rotation_interval_seconds')
    @classmethod
    def validate_activity_rotation_interval(cls, v: int) -> int:
        if v < 15:
            raise ValueError('Activity rotation interval must be at least 15 seconds')
        return v
    

from typing import Optional
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Discord
    discord_token: SecretStr
    discord_guild_id: Optional[int] = None
    discord_owner_id: int
    discord_proxy_url: Optional[str] = None

    # Database
    database_url: str

    # Optional IDs for channels and roles
    auto_role_id: Optional[int] = None

    log_channel_id: Optional[int] = None
    welcome_channel_id: Optional[int] = None

    # Logging
    log_level: str = "INFO"

    # Retention
    message_log_retention_days: int = 30
    punishment_retention_days: int = 365
    retention_cleanup_interval_hours: int = 6

    command_prefix: str = "!"
    activity_name: str = "Omnibot | центр управления"
    bot_status: str = "online"
    activity_rotation_enabled: bool = True
    activity_rotation_interval_seconds: int = 600
    presence_activities: str = ""

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
    

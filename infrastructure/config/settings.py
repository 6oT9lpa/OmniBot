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
    discord_proxy_url: Optional[str] = None

    # Database
    database_url: str

    # Logging
    log_level: str = "INFO"

    # Retention
    message_log_retention_days: int = 30
    punishment_retention_days: int = 365
    retention_cleanup_interval_hours: int = 6

    command_prefix: str = "!"
    activity_rotation_enabled: bool = True
    activity_rotation_interval_seconds: int = 600

    twitch_client_id: Optional[str] = None
    twitch_client_secret: Optional[SecretStr] = None
    youtube_api_key: Optional[SecretStr] = None

    @field_validator('activity_rotation_interval_seconds')
    @classmethod
    def validate_activity_rotation_interval(cls, v: int) -> int:
        if v < 15:
            raise ValueError('Activity rotation interval must be at least 15 seconds')
        return v
    

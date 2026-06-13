from functools import lru_cache
from infrastructure.config.settings import BotConfig


@lru_cache(maxsize=1)
def get_config() -> BotConfig:
    # Singleton instance of BotConfig, cached for performance
    return BotConfig()


def reload_config() -> BotConfig:
    # Clear the cache to force reloading the configuration
    get_config.cache_clear()
    return get_config()
from typing import Any, Optional


def normalize_config(config: Optional[dict[str, Any]], guild_id: int) -> dict[str, Any]:
    config = config or {}
    return {
        "guild_id": str(guild_id),
        "title": config.get("title") or "Welcome!",
        "description": config.get("description") or "Hi, {user}! Welcome to {guild}.",
        "thumbnail_url": config.get("thumbnail_url"),
        "footer_text": config.get("footer_text"),
        "footer_icon_url": config.get("footer_icon_url"),
        "color": config.get("color") or 0x57F287,
        "is_enabled": config.get("is_enabled", 1) != 0,
        "rules_channel_id": _snowflake_or_none(config.get("rules_channel_id")),
        "roles_channel_id": _snowflake_or_none(config.get("roles_channel_id")),
    }


def _snowflake_or_none(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)

from __future__ import annotations

import re


MODULE_ORDER = (
    "dashboard",
    "access",
    "welcome",
    "role-panels",
    "creator-alerts",
    "dev-blog",
    "ai-moderator",
    "logs",
    "server-stats",
    "voice-rooms",
    "bot-settings",
    "integrations",
    "health",
)

PERMISSION_ORDER = ("disabled", "view", "edit", "publish", "manage")

BUILTIN_ACCESS_ROLES: tuple[dict[str, object], ...] = (
    {"slug": "user", "name": "User", "modules": {"dashboard": "view", "health": "view"}},
    {"slug": "creator", "name": "Creator", "modules": {"dashboard": "view", "creator-alerts": "edit", "health": "view"}},
    {"slug": "developer", "name": "Developer", "modules": {"dashboard": "view", "dev-blog": "publish", "health": "view"}},
    {"slug": "moderator", "name": "Moderator", "modules": {"dashboard": "view", "ai-moderator": "view", "logs": "view", "health": "view"}},
    {"slug": "administrator", "name": "Administrator", "modules": {key: "manage" for key in MODULE_ORDER}},
)


def normalize_access_role_slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return value.strip("-") or "custom-role"


def normalize_permission(permission: str) -> str:
    return permission if permission in PERMISSION_ORDER else "disabled"


def normalize_module_permissions(modules: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key in MODULE_ORDER:
        normalized[key] = normalize_permission(modules.get(key, "disabled"))
    return normalized


def merge_module_permissions(rows: list[dict[str, str]]) -> dict[str, str]:
    merged = {key: "disabled" for key in MODULE_ORDER}
    for row in rows:
        for key, permission in row.items():
            if key not in merged:
                continue
            if PERMISSION_ORDER.index(normalize_permission(permission)) > PERMISSION_ORDER.index(merged[key]):
                merged[key] = normalize_permission(permission)
    return merged

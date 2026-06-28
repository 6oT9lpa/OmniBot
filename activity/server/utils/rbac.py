from __future__ import annotations

import re

from core.domain.activity_access import (
    ACCESS_ROLE_CONFIGURABLE_MODULES,
    BUILTIN_ACCESS_ROLES,
    DEFAULT_VISIBLE_MODULES,
    MODULE_ORDER,
    PERMISSION_ORDER,
)


def normalize_access_role_slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return value.strip("-") or "custom-role"


def normalize_permission(permission: str) -> str:
    return permission if permission in PERMISSION_ORDER else "disabled"


def normalize_module_permissions(modules: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {key: "disabled" for key in MODULE_ORDER}
    for key in DEFAULT_VISIBLE_MODULES:
        normalized[key] = "view"
    for key in ACCESS_ROLE_CONFIGURABLE_MODULES:
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

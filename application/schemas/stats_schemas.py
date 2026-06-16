from __future__ import annotations

from pydantic import BaseModel, Field


class StatsQuerySchema(BaseModel):
    """Параметры запроса статистики сервера."""

    guild_id: int = Field(gt=0)
    period: int = Field(ge=1, le=90, default=7)


class LeaderboardQuerySchema(BaseModel):
    """Параметры запроса лидерборда."""

    guild_id: int = Field(gt=0)
    days: int = Field(ge=1, le=90, default=7)
    limit: int = Field(ge=1, le=50, default=10)


class UserStatsQuerySchema(BaseModel):
    """Параметры запроса статистики пользователя."""

    user_id: int = Field(gt=0)
    guild_id: int = Field(gt=0)
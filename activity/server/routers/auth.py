import asyncio
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, HTTPException

from activity.server.schemas.auth import TokenRequest, TokenResponse
from activity.server.services.auth_service import ActivityAuthService
from infrastructure.config import get_config

router = APIRouter()
service = ActivityAuthService()
_exchange_timestamps: deque[float] = deque()
_exchange_limit_lock = asyncio.Lock()


@router.post("/api/auth/token", response_model=TokenResponse)
async def exchange_token(payload: TokenRequest) -> dict[str, Any]:
    await _enforce_exchange_rate_limit()
    return await service.exchange_token(payload)


async def _enforce_exchange_rate_limit() -> None:
    now = time.monotonic()
    limit = max(1, get_config().activity_token_exchange_limit_per_minute)
    async with _exchange_limit_lock:
        while _exchange_timestamps and now - _exchange_timestamps[0] >= 60:
            _exchange_timestamps.popleft()
        if len(_exchange_timestamps) >= limit:
            retry_after = max(1, round(60 - (now - _exchange_timestamps[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many token exchange requests",
                headers={"Retry-After": str(retry_after)},
            )
        _exchange_timestamps.append(now)

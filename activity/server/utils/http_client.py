from __future__ import annotations

import httpx

from infrastructure.config import get_config


def discord_async_client(timeout: float | httpx.Timeout = 10) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        proxy=get_config().discord_proxy_url,
        # OAuth and bot credentials must never be sent to an ambient HTTP_PROXY.
        # A proxy, when required, is configured explicitly via DISCORD_PROXY_URL.
        trust_env=False,
    )

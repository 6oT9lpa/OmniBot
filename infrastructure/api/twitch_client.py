from __future__ import annotations

from typing import Optional

import aiohttp

from core.domain.creator_alert import (
    CreatorAlertKind,
    CreatorContentEvent,
    CreatorPlatform,
)
from core.interfaces.clients import CreatorPlatformClientInterface
from infrastructure.api.url_parser import CreatorUrlParser
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class TwitchClient(CreatorPlatformClientInterface):
    def __init__(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
        proxy_url: Optional[str] = None,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._proxy_url = proxy_url
        self._token: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def fetch_latest_event(
        self,
        channel_url: str,
        external_channel_id: Optional[str] = None,
    ) -> Optional[CreatorContentEvent]:
        if not self.is_configured:
            logger.info("Twitch credentials are not configured")
            return None

        login = external_channel_id or CreatorUrlParser.twitch_login(channel_url)
        if not login:
            logger.warning("Unable to parse Twitch login from url=%s", channel_url)
            return None

        token = await self._get_app_token()
        headers = {
            "Client-ID": self._client_id,
            "Authorization": f"Bearer {token}",
        }
        async with aiohttp.ClientSession() as session:
            logger.info("Fetching Twitch stream login=%s", login)
            async with session.get(
                "https://api.twitch.tv/helix/streams",
                headers=headers,
                params={"user_login": login},
                proxy=self._proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    logger.warning("Twitch stream request failed status=%s body=%s", response.status, text[:300])
                    return None
                payload = await response.json()

        data = payload.get("data") or []
        if not data:
            logger.info("Twitch stream is offline login=%s", login)
            return None

        stream = data[0]
        return CreatorContentEvent(
            platform=CreatorPlatform.TWITCH,
            alert_kind=CreatorAlertKind.STREAM,
            event_id=str(stream["id"]),
            creator_name=stream.get("user_name") or login,
            title=stream.get("title") or "Live stream",
            url=f"https://www.twitch.tv/{login}",
            game=stream.get("game_name"),
            thumbnail_url=(stream.get("thumbnail_url") or "").replace("{width}", "1280").replace("{height}", "720"),
        )

    async def _get_app_token(self) -> str:
        if self._token:
            return self._token

        async with aiohttp.ClientSession() as session:
            logger.info("Requesting Twitch app token")
            async with session.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "client_credentials",
                },
                proxy=self._proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        self._token = payload["access_token"]
        return self._token

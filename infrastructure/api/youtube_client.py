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


class YouTubeClient(CreatorPlatformClientInterface):
    def __init__(self, api_key: Optional[str], proxy_url: Optional[str] = None):
        self._api_key = api_key
        self._proxy_url = proxy_url

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def fetch_latest_event(
        self,
        channel_url: str,
        external_channel_id: Optional[str] = None,
    ) -> Optional[CreatorContentEvent]:
        if not self.is_configured:
            logger.info("YouTube API key is not configured")
            return None

        channel_ref = external_channel_id or CreatorUrlParser.youtube_channel_ref(channel_url)
        channel_id = await self._resolve_channel_id(channel_ref)
        if not channel_id:
            logger.warning("Unable to resolve YouTube channel ref=%s", channel_ref)
            return None

        live_event = await self._search(channel_id, event_type="live")
        if live_event:
            return live_event
        return await self._search(channel_id, event_type=None)

    async def _resolve_channel_id(self, channel_ref: str) -> Optional[str]:
        if channel_ref.startswith("UC"):
            return channel_ref
        if not channel_ref.startswith("@"):
            return channel_ref

        handle = channel_ref[1:]
        async with aiohttp.ClientSession() as session:
            logger.info("Resolving YouTube handle with channels.list handle=%s", channel_ref)
            async with session.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "id,snippet",
                    "forHandle": handle,
                    "key": self._api_key,
                },
                proxy=self._proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status < 400:
                    payload = await response.json()
                    items = payload.get("items") or []
                    if items:
                        return items[0]["id"]
                logger.warning("YouTube channels.list handle resolve failed status=%s", response.status)

        async with aiohttp.ClientSession() as session:
            logger.info("Resolving YouTube handle with search fallback handle=%s", channel_ref)
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": channel_ref,
                    "type": "channel",
                    "maxResults": 1,
                    "key": self._api_key,
                },
                proxy=self._proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status >= 400:
                    logger.warning("YouTube channel resolve failed status=%s", response.status)
                    return None
                payload = await response.json()
        items = payload.get("items") or []
        return items[0]["snippet"]["channelId"] if items else None

    async def _search(
        self,
        channel_id: str,
        event_type: Optional[str],
    ) -> Optional[CreatorContentEvent]:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": 1,
            "key": self._api_key,
        }
        if event_type:
            params["eventType"] = event_type

        async with aiohttp.ClientSession() as session:
            logger.info("Fetching YouTube event channel_id=%s event_type=%s", channel_id, event_type or "latest")
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                proxy=self._proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status >= 400:
                    logger.warning("YouTube search failed status=%s", response.status)
                    return None
                payload = await response.json()

        items = payload.get("items") or []
        if not items:
            return None
        item = items[0]
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        thumbnails = snippet.get("thumbnails") or {}
        image = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}
        is_live = event_type == "live" or snippet.get("liveBroadcastContent") == "live"
        return CreatorContentEvent(
            platform=CreatorPlatform.YOUTUBE,
            alert_kind=CreatorAlertKind.STREAM if is_live else CreatorAlertKind.VIDEO,
            event_id=video_id,
            creator_name=snippet.get("channelTitle") or "YouTube",
            title=snippet.get("title") or "New YouTube publication",
            url=f"https://www.youtube.com/watch?v={video_id}",
            thumbnail_url=image.get("url"),
        )

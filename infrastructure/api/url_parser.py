from __future__ import annotations

from urllib.parse import parse_qs, urlparse


class CreatorUrlParser:
    @staticmethod
    def twitch_login(channel_url: str) -> str:
        parsed = urlparse(channel_url.strip())
        if not parsed.netloc:
            return channel_url.strip().lstrip("@")
        parts = [part for part in parsed.path.split("/") if part]
        return parts[0].lstrip("@") if parts else ""

    @staticmethod
    def youtube_channel_ref(channel_url: str) -> str:
        value = channel_url.strip()
        parsed = urlparse(value)
        if not parsed.netloc:
            return value
        query = parse_qs(parsed.query)
        if "channel_id" in query:
            return query["channel_id"][0]
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0].lower() in {"channel", "c"}:
            return parts[1]
        if parts and parts[0].startswith("@"):
            return parts[0]
        return value

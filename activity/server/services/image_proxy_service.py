import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import HTTPException

from infrastructure.logging import get_logger


logger = get_logger(__name__)


class ImageProxyService:
    _allowed_content_types = {
        "image/avif",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    _max_bytes = 10 * 1024 * 1024
    _max_redirects = 3

    async def fetch_image(self, url: str) -> tuple[bytes, str]:
        current_url = url
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            for redirect_count in range(self._max_redirects + 1):
                hostname = await self._validate_url(current_url)
                logger.info("Fetching Activity preview image host=%s redirect=%s", hostname, redirect_count)

                try:
                    async with client.stream(
                        "GET",
                        current_url,
                        headers={"Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif"},
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location or redirect_count >= self._max_redirects:
                                raise HTTPException(status_code=502, detail="Image redirect limit exceeded")
                            current_url = urljoin(current_url, location)
                            continue

                        if response.status_code >= 400:
                            logger.warning("Preview image upstream rejected request host=%s status=%s", hostname, response.status_code)
                            raise HTTPException(status_code=502, detail="Image source is unavailable")

                        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                        if content_type not in self._allowed_content_types:
                            raise HTTPException(status_code=415, detail="URL does not contain a supported image")

                        content_length = response.headers.get("content-length")
                        if content_length and int(content_length) > self._max_bytes:
                            raise HTTPException(status_code=413, detail="Image exceeds the 10 MB preview limit")

                        chunks: list[bytes] = []
                        size = 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > self._max_bytes:
                                raise HTTPException(status_code=413, detail="Image exceeds the 10 MB preview limit")
                            chunks.append(chunk)

                        logger.info("Activity preview image loaded host=%s bytes=%s", hostname, size)
                        return b"".join(chunks), content_type
                except HTTPException:
                    raise
                except (httpx.HTTPError, ValueError) as error:
                    logger.warning("Preview image request failed host=%s error=%s", hostname, type(error).__name__)
                    raise HTTPException(status_code=502, detail="Image source is unavailable") from error

        raise HTTPException(status_code=502, detail="Image source is unavailable")

    async def _validate_url(self, url: str) -> str:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise HTTPException(status_code=400, detail="Preview image must use a public HTTPS URL")
        try:
            port = parsed.port
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Preview image URL has an invalid port") from error
        if port not in (None, 443):
            raise HTTPException(status_code=400, detail="Preview image URL uses an unsupported port")

        try:
            addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, 443, type=socket.SOCK_STREAM)
        except socket.gaierror as error:
            raise HTTPException(status_code=400, detail="Preview image hostname cannot be resolved") from error

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                logger.warning("Rejected non-public preview image host=%s address=%s", parsed.hostname, ip)
                raise HTTPException(status_code=400, detail="Preview image must use a public host")

        return parsed.hostname

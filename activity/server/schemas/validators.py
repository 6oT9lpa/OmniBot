from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlparse


def validate_public_https_url(value: str) -> str:
    """Validate URLs that Discord will render or fetch on behalf of a user."""
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("Only absolute HTTPS URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")

    host = parsed.hostname
    if not host or host.lower() == "localhost" or host.lower().endswith(".localhost"):
        raise ValueError("Loopback URLs are not allowed")
    try:
        address = ip_address(host)
    except ValueError:
        return normalized

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
        or address.is_multicast
    ):
        raise ValueError("Private and non-public IP addresses are not allowed")
    return normalized

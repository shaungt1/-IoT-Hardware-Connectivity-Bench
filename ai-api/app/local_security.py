from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit


LOCAL_NAMES = {"localhost", "testclient"}


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().strip("[]").lower()
    if normalized in LOCAL_NAMES:
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_local_origin(origin: str | None) -> bool:
    if not origin:
        return True
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and is_loopback_host(parsed.hostname)


def local_request_allowed(client_host: str | None, origin: str | None = None) -> bool:
    return is_loopback_host(client_host) and is_local_origin(origin)

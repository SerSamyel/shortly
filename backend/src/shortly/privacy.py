"""Turn request data into the privacy-safe fields of a click event.

Raw IP addresses never leave this module: they become a country code and a
visitor hash that only links visits within one UTC day.
"""

import hashlib
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from starlette.requests import Request


def client_ip(request: "Request", trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def visitor_hash(salt: str, ip: str, user_agent: str) -> str:
    return hashlib.sha256(f"{salt}|{ip}|{user_agent}".encode()).hexdigest()


def referrer_domain(referer: str | None, own_host: str = "") -> str:
    if not referer:
        return "direct"
    try:
        host = (urlsplit(referer).hostname or "").lower()
    except ValueError:
        return "direct"
    if not host:
        return "direct"
    host = host.removeprefix("www.")
    if own_host and host == own_host:
        return "direct"
    return host[:255]

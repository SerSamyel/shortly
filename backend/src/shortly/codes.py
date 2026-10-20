"""Short codes, aliases and target URL rules (see _docs/plan.md, section 4.2)."""

import re
import secrets
import string
from urllib.parse import urlsplit

CODE_ALPHABET = string.ascii_lowercase + string.digits
CODE_LENGTH = 7
MAX_URL_LENGTH = 2048

# Paths the SPA and the API use; a link must never shadow them.
RESERVED_WORDS = frozenset(
    {"api", "app", "login", "signup", "health", "metrics", "static", "assets", "docs"}
)

ALIAS_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(code: str) -> str:
    return code.strip().lower()


def alias_error(alias: str) -> str | None:
    """Return a user-facing error for an invalid alias, or None if it is fine."""
    if not 3 <= len(alias) <= 32:
        return "Alias must be 3 to 32 characters long"
    if not ALIAS_RE.fullmatch(alias):
        return (
            "Alias may contain only letters, digits and '-', "
            "and cannot start or end with '-'"
        )
    if alias in RESERVED_WORDS:
        return f"Alias '{alias}' is reserved"
    return None


def target_url_error(url: str, own_host: str) -> str | None:
    """Return a user-facing error for an unacceptable target URL, or None if it is fine."""
    if len(url) > MAX_URL_LENGTH:
        return f"URL must be at most {MAX_URL_LENGTH} characters"
    if any(ch.isspace() for ch in url):
        return "URL must not contain spaces"
    try:
        parts = urlsplit(url)
    except ValueError:
        return "URL is not valid"
    if parts.scheme.lower() not in {"http", "https"}:
        return "Only http and https URLs can be shortened"
    host = (parts.hostname or "").lower()
    if not host:
        return "URL must include a host"
    if own_host and host == own_host:
        return "Links to this service cannot be shortened"
    return None

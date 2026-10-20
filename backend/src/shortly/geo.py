"""Country lookup from a local MaxMind-format database (DB-IP Lite or GeoLite2)."""

import ipaddress
import logging
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)

UNKNOWN = "unknown"


class CountryLookup(Protocol):
    def country(self, ip: str) -> str: ...
    def close(self) -> None: ...


class NoGeo:
    def country(self, ip: str) -> str:
        return UNKNOWN

    def close(self) -> None:
        return None


class MmdbGeo:
    def __init__(self, path: str) -> None:
        import maxminddb

        self.reader = maxminddb.open_database(path)

    def country(self, ip: str) -> str:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return UNKNOWN
        if address.is_private or address.is_loopback:
            return UNKNOWN
        try:
            record = self.reader.get(str(address))
        except ValueError:
            return UNKNOWN
        if not isinstance(record, dict):
            return UNKNOWN
        code = (record.get("country") or {}).get("iso_code")
        return code if isinstance(code, str) else UNKNOWN

    def close(self) -> None:
        self.reader.close()


def load_geo(path: str | None) -> CountryLookup:
    if path and Path(path).is_file():
        log.info("geoip database loaded", extra={"geoip_path": path})
        return MmdbGeo(path)
    if path:
        log.warning("geoip database not found; countries will be 'unknown'")
    return NoGeo()

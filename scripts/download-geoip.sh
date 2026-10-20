#!/usr/bin/env sh
# Downloads DB-IP "IP to Country Lite" (CC BY 4.0, https://db-ip.com) into geoip/.
set -eu
cd "$(dirname "$0")/.."
mkdir -p geoip
month=$(date -u +%Y-%m)
url="https://download.db-ip.com/free/dbip-country-lite-${month}.mmdb.gz"
echo "Downloading ${url}"
curl -fsSL "$url" | gunzip > geoip/dbip-country-lite.mmdb
echo "Saved geoip/dbip-country-lite.mmdb"

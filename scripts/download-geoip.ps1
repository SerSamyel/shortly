# Downloads DB-IP "IP to Country Lite" (CC BY 4.0, https://db-ip.com) into geoip\ (Windows).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path "$root\geoip" | Out-Null
$month = (Get-Date).ToUniversalTime().ToString("yyyy-MM")
$url = "https://download.db-ip.com/free/dbip-country-lite-$month.mmdb.gz"
$gz = "$root\geoip\dbip.mmdb.gz"
Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $gz
$in = [IO.File]::OpenRead($gz)
$out = [IO.File]::Create("$root\geoip\dbip-country-lite.mmdb")
$gzip = New-Object IO.Compression.GZipStream($in, [IO.Compression.CompressionMode]::Decompress)
$gzip.CopyTo($out)
$gzip.Close(); $out.Close(); $in.Close()
Remove-Item $gz
Write-Host "Saved geoip\dbip-country-lite.mmdb"

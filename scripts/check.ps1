# Runs every check and writes one log per step into logs\ (Windows).
# Usage: scripts\check.cmd [step ...]   steps: backend frontend deps integration build
param([string[]]$Steps = @("backend", "frontend", "deps", "integration"))

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
Remove-Item (Join-Path $logs "*.txt") -ErrorAction SilentlyContinue
$env:PYTHONIOENCODING = "utf-8"
$env:NO_COLOR = "1"
$env:FORCE_COLOR = "0"

function Run-Step([string]$name, [string]$dir, [scriptblock]$body) {
    $log = Join-Path $logs "$name.txt"
    Write-Host "=== $name ===" -ForegroundColor Cyan
    Push-Location (Join-Path $root $dir)
    $started = Get-Date
    try {
        & $body 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log
        $code = $LASTEXITCODE
    } catch {
        $_ | Out-File -Append $log
        $code = 1
    }
    Pop-Location
    $secs = [int]((Get-Date) - $started).TotalSeconds
    "$name exit=$code seconds=$secs" | Out-File -Append -Encoding utf8 (Join-Path $logs "summary.txt")
}

foreach ($step in $Steps) {
    switch ($step) {
        "backend" {
            Run-Step "backend-unit" "backend" { uv sync; uv run pytest -q -p no:cacheprovider }
        }
        "frontend" {
            if (Get-Command npm -ErrorAction SilentlyContinue) {
                Run-Step "frontend-unit" "frontend" { npm install --no-fund --no-audit; npm test; npx tsc -b }
            } else {
                # No Node.js on this machine: run the same commands in a container.
                # node_modules lives in an anonymous volume so Linux binaries never land in the repo.
                Run-Step "frontend-unit" "frontend" {
                    docker run --rm -v "${PWD}:/app" -v /app/node_modules -w /app -e CI=1 node:22-alpine `
                        sh -c "npm install --no-fund --no-audit && npm test && npx tsc -b"
                }
            }
        }
        "deps" {
            Run-Step "deps" "." { docker compose up -d --wait postgres redis redpanda; docker compose ps }
        }
        "integration" {
            $env:TEST_DATABASE_URL = "postgresql+asyncpg://shortly:shortly@localhost:5432/shortly_test"
            $env:TEST_REDIS_URL = "redis://localhost:6379/15"
            $env:TEST_KAFKA_BOOTSTRAP = "localhost:19092"
            Run-Step "integration" "backend" { uv run pytest tests_integration -q -p no:cacheprovider }
        }
        "build" {
            Run-Step "compose-build" "." { docker compose build }
        }
        "up" {
            Run-Step "compose-up" "." { docker compose up -d --build --wait app consumer; docker compose ps; docker compose logs --tail 60 app consumer migrate }
        }
    }
}
"done" | Out-File -Encoding utf8 (Join-Path $logs "done.txt")
Write-Host "Logs are in $logs" -ForegroundColor Green

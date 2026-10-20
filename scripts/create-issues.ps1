# Creates GitHub issues from _docs/backlog/*.md (Windows). Needs the GitHub CLI: winget install GitHub.cli; gh auth login
# Each file: "title: ..." and "labels: a,b" lines, then "---", then the issue body. Existing titles are skipped.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
# Find gh even when PATH has not been refreshed after installation.
$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
$gh = if ($ghCmd) { $ghCmd.Source } else { "$env:ProgramFiles\GitHub CLI\gh.exe" }
if (-not (Test-Path $gh)) {
    Write-Host "GitHub CLI not found. Install it: winget install GitHub.cli, then run: gh auth login" -ForegroundColor Red
    exit 1
}
& $gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "Not logged in. Run: & $gh auth login" -ForegroundColor Red; exit 1 }

$labels = @{
    "groomed" = "0e8a16"; "security" = "b60205"; "frontend" = "1d76db"; "backend" = "5319e7";
    "ci" = "fbca04"; "testing" = "c2e0c6"; "observability" = "d93f0b"; "agents" = "006b75"; "deploy" = "0052cc"
}
foreach ($name in $labels.Keys) { & $gh label create $name --color $labels[$name] --force | Out-Null }

$existing = & $gh issue list --state all --limit 200 --json title --jq ".[].title"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$tmp = Join-Path $env:TEMP "shortly-issue-body.md"

foreach ($file in Get-ChildItem "$root\_docs\backlog\*.md" | Sort-Object Name) {
    $text = [IO.File]::ReadAllText($file.FullName, $utf8) -replace "`r`n", "`n"
    $parts = $text -split "`n---`n", 2
    $title = ([regex]::Match($parts[0], "(?m)^title:\s*(.+)$")).Groups[1].Value.Trim()
    $issueLabels = ([regex]::Match($parts[0], "(?m)^labels:\s*(.+)$")).Groups[1].Value.Trim()
    if ($existing -contains $title) { Write-Host "skip (exists): $title"; continue }
    [IO.File]::WriteAllText($tmp, $parts[1].Trim(), $utf8)
    $url = & $gh issue create --title $title --body-file $tmp --label $issueLabels
    Write-Host "created: $url"
}
Remove-Item $tmp -ErrorAction SilentlyContinue

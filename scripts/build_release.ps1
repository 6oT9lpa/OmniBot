param(
    [string]$Archive = (Join-Path $env:TEMP 'omnibot-release.tar.gz')
)

$ErrorActionPreference = 'Stop'

if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive
}

tar --exclude='./.git' `
    --exclude='./venv' `
    --exclude='./.venv' `
    --exclude='./activity/client/node_modules' `
    --exclude='./data' `
    --exclude='./logs' `
    --exclude='./.env' `
    --exclude='./__pycache__' `
    --exclude='./.pytest_cache' `
    --exclude='./htmlcov' `
    --exclude='./.coverage' `
    -czf $Archive .

Write-Host "Release archive created: $Archive"

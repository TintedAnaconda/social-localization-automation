# scripts/stop.ps1
$ErrorActionPreference = "Stop"

Write-Host "Stopping n8n..." -ForegroundColor Cyan
docker compose down

Write-Host "n8n stopped." -ForegroundColor Green
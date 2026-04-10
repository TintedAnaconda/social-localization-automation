# scripts/start.ps1
$ErrorActionPreference = "Stop"

Write-Host "Starting n8n..." -ForegroundColor Cyan
docker compose up -d

Write-Host ""
Write-Host "n8n should be available at: http://localhost:5678" -ForegroundColor Green
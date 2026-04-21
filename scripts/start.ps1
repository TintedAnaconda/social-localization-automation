$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Starting QA Automation..." -ForegroundColor Cyan

# Resolve repo root from the script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

# Check that n8n is installed
try {
    $n8nVersion = & n8n --version
    Write-Host "n8n detected: $n8nVersion" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: n8n is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install it with: npm install -g n8n"
    exit 1
}

# Set environment variables needed for your workflow
$env:NODES_EXCLUDE = "[]"
$env:N8N_HOST = "localhost"
$env:N8N_PORT = "5678"
$env:N8N_PROTOCOL = "http"

# Optional: suppress settings permission warnings on Windows
$env:N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS = "false"

# Check if n8n is already running on port 5678
$existing = netstat -ano | Select-String ":5678"
if ($existing) {
    Write-Host "n8n may already be running on port 5678." -ForegroundColor Yellow
    Write-Host "If localhost does not work, stop the existing process first." -ForegroundColor Yellow
}

# Start n8n in a separate PowerShell window and keep that window open
$command = @"
Set-Location '$RepoRoot'
`$env:NODES_EXCLUDE='[]'
`$env:N8N_HOST='localhost'
`$env:N8N_PORT='5678'
`$env:N8N_PROTOCOL='http'
`$env:N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS='false'
n8n
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $command | Out-Null

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "n8n start command launched." -ForegroundColor Green
Write-Host "Open your browser manually and go to: http://localhost:5678" -ForegroundColor Cyan
Write-Host ""
Write-Host "Leave the n8n PowerShell window open while automation is running." -ForegroundColor Yellow
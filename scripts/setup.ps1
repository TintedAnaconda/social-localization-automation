$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Starting QA Automation..." -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

try {
    $n8nVersion = & n8n --version
    Write-Host "n8n detected: $n8nVersion" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: n8n is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install it with: npm install -g n8n"
    exit 1
}

$cmd = "cd /d `"$RepoRoot`" && set NODES_EXCLUDE=[] && set N8N_HOST=localhost && set N8N_PORT=5678 && set N8N_PROTOCOL=http && n8n"

Start-Process cmd.exe -ArgumentList "/k", $cmd | Out-Null

Write-Host ""
Write-Host "A new command window should open and keep n8n running." -ForegroundColor Green
Write-Host "Wait until that window says: http://localhost:5678" -ForegroundColor Cyan
Write-Host "Then open your browser manually." -ForegroundColor Cyan
Write-Host ""

# scripts/start.ps1
# Starts local n8n in a separate PowerShell window and opens the browser.
# Run from repo root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1

$ErrorActionPreference = 'Stop'

function Write-Step($message) {
    Write-Host ""
    Write-Host "=== $message ===" -ForegroundColor Cyan
}

function Test-CommandExists($command) {
    return $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $repoRoot 'n8n\n8n.pid'
$logDir = Join-Path $repoRoot 'logs'
$workflowDir = Join-Path $repoRoot 'n8n'
$env:N8N_USER_FOLDER = $workflowDir

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
if (-not (Test-Path $workflowDir)) {
    New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
}

if (-not (Test-CommandExists 'n8n')) {
    Write-Error 'n8n is not installed or not on PATH. Run .\scripts\setup.ps1 first.'
}

if (Test-Path $pidFile) {
    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($existingPid) {
        $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($existingProcess) {
            Write-Host "n8n appears to already be running (PID $existingPid)." -ForegroundColor Yellow
            Start-Process 'http://localhost:5678' | Out-Null
            exit 0
        }
        else {
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Step "Starting local n8n"

$command = @"
`$env:NODES_EXCLUDE='[]'
`$env:N8N_HOST='localhost'
`$env:N8N_PORT='5678'
`$env:N8N_PROTOCOL='http'
`$env:N8N_USER_FOLDER='$workflowDir'
n8n
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
$process = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $encoded `
    -PassThru -WorkingDirectory $repoRoot

Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII
Write-Host "Started n8n in a new window (PID $($process.Id))." -ForegroundColor Green

Start-Sleep -Seconds 4
Start-Process 'http://localhost:5678' | Out-Null

Write-Host ''
Write-Host 'n8n should now be available at: http://localhost:5678' -ForegroundColor Green
Write-Host 'Keep the n8n PowerShell window open while automation is running.' -ForegroundColor Yellow

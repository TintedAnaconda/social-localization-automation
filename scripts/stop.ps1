# scripts/stop.ps1
# Stops local n8n started by start.ps1.
# Run from repo root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\stop.ps1

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $repoRoot 'n8n\n8n.pid'

Write-Host 'Stopping local n8n...' -ForegroundColor Cyan

if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($pid) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $pid -Force
            Write-Host "Stopped n8n process $pid." -ForegroundColor Green
        }
        else {
            Write-Host 'n8n process was not running, but the PID file existed.' -ForegroundColor Yellow
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
else {
    Write-Host 'No PID file found. Trying to stop any running n8n process by name...' -ForegroundColor Yellow
    Get-Process -Name 'node' -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like '*node.exe'
    } | ForEach-Object {
        # Intentionally conservative: only stop processes if their command line includes n8n
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            if ($cmdLine -and $cmdLine -match 'n8n') {
                Stop-Process -Id $_.Id -Force
                Write-Host "Stopped n8n-related node process $($_.Id)." -ForegroundColor Green
            }
        }
        catch {
            # Ignore lookup failures and continue.
        }
    }
}

Write-Host 'n8n stop command completed.' -ForegroundColor Green

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Stopping QA Automation..." -ForegroundColor Cyan

# Find n8n processes
$N8nProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "node.exe" -and $_.CommandLine -match "n8n"
}

if (-not $N8nProcesses) {
    Write-Host "No running n8n process found." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

foreach ($proc in $N8nProcesses) {
    try {
        Stop-Process -Id $proc.ProcessId -Force
        Write-Host "Stopped n8n process ID $($proc.ProcessId)" -ForegroundColor Green
    }
    catch {
        Write-Host "Could not stop process ID $($proc.ProcessId)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "QA Automation stopped." -ForegroundColor Green
Write-Host ""
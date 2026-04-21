# scripts/setup.ps1
# One-time setup for local Python + local n8n
# Run from repo root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

$ErrorActionPreference = 'Stop'

function Write-Step($message) {
    Write-Host ""
    Write-Host "=== $message ===" -ForegroundColor Cyan
}

function Test-CommandExists($command) {
    return $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

function Get-PythonCommand {
    if (Test-CommandExists 'py') { return 'py' }
    if (Test-CommandExists 'python') { return 'python' }
    throw 'Python is not installed or not on PATH. Please install Python 3.11+ first.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

Write-Step "Using repository folder"
Write-Host $repoRoot -ForegroundColor Green

Write-Step "Checking required tools"

if (-not (Test-CommandExists 'node')) {
    Write-Error 'Node.js is not installed or not on PATH. Please install Node.js LTS first.'
}

if (-not (Test-CommandExists 'npm')) {
    Write-Error 'npm is not installed or not on PATH. Please install Node.js LTS first.'
}

$pythonCmd = Get-PythonCommand
Write-Host "Python command found: $pythonCmd" -ForegroundColor Green
Write-Host 'Node.js found.' -ForegroundColor Green
Write-Host 'npm found.' -ForegroundColor Green

if (Test-CommandExists 'git') {
    Write-Host 'Git found.' -ForegroundColor Green
}
else {
    Write-Host 'Git not found. This is OK if the repo was downloaded manually.' -ForegroundColor Yellow
}

Write-Step "Creating required folders"

$folders = @(
    'input',
    'input\processed',
    'output',
    'output\qa_reports',
    'logs',
    'config',
    'templates'
)

foreach ($folder in $folders) {
    $fullPath = Join-Path $repoRoot $folder
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "Created $folder" -ForegroundColor Green
    }
    else {
        Write-Host "Exists: $folder"
    }
}

Write-Step "Creating Python virtual environment"

$venvPath = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    & $pythonCmd -m venv $venvPath
    Write-Host 'Virtual environment created.' -ForegroundColor Green
}
else {
    Write-Host '.venv already exists'
}

if (-not (Test-Path $venvPython)) {
    Write-Error "Could not find virtual environment Python at $venvPython"
}

Write-Step "Installing Python packages"

& $venvPython -m pip install --upgrade pip

$requirementsFile = Join-Path $repoRoot 'requirements.txt'
if (Test-Path $requirementsFile) {
    & $venvPython -m pip install -r $requirementsFile
    Write-Host 'requirements.txt installed successfully.' -ForegroundColor Green
}
else {
    Write-Host 'requirements.txt not found. Skipping Python package install.' -ForegroundColor Yellow
}

Write-Step "Creating local .env file"

$envExample = Join-Path $repoRoot '.env.example'
$envFile = Join-Path $repoRoot '.env'

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host 'Created .env from .env.example' -ForegroundColor Green
    }
    else {
        Write-Host '.env.example not found. Skipping .env creation.' -ForegroundColor Yellow
    }
}
else {
    Write-Host '.env already exists'
}

Write-Step "Checking n8n installation"

if (Test-CommandExists 'n8n') {
    Write-Host 'n8n is already installed.' -ForegroundColor Green
}
else {
    Write-Host 'n8n not found. Installing globally with npm...' -ForegroundColor Yellow
    npm install -g n8n
    if (-not (Test-CommandExists 'n8n')) {
        Write-Error 'n8n install finished but the n8n command is still not available. Close this terminal, open a new PowerShell window, and run setup again.'
    }
    Write-Host 'n8n installed successfully.' -ForegroundColor Green
}

Write-Step "Writing local setup notes"

$notesPath = Join-Path $repoRoot 'LOCAL_SETUP_NOTES.txt'
$notes = @"
Local setup is complete.

Next steps:
1. Run .\scripts\start.ps1 to start local n8n.
2. Open http://localhost:5678 if it does not open automatically.
3. Import the shared workflow JSON into n8n if this is the first setup.
4. In the Execute Command node, use the repo virtual environment Python:
   cd /d "$repoRoot" && .\.venv\Scripts\python.exe automation\qa_engine.py 2>&1
5. Drop Excel files into:
   $repoRoot\input
6. Find QA reports in:
   $repoRoot\output\qa_reports
"@
Set-Content -Path $notesPath -Value $notes -Encoding UTF8
Write-Host "Created LOCAL_SETUP_NOTES.txt" -ForegroundColor Green

Write-Step "Setup complete"
Write-Host 'Run .\scripts\start.ps1 to launch local n8n.' -ForegroundColor Cyan

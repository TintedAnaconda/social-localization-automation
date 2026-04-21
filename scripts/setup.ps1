$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "QA Automation Setup" -ForegroundColor Cyan
Write-Host "-------------------" -ForegroundColor Cyan

# Resolve repo root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Write-Host "Repo root: $RepoRoot" -ForegroundColor Gray

# Helper function
function Test-Command {
    param([string]$CommandName)
    return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

# -----------------------------------
# 1. Check prerequisites
# -----------------------------------

# Detect Python command
$PythonCmd = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
}
else {
    Write-Host ""
    Write-Host "ERROR: Python is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Please install Python and re-run setup." -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python command: $PythonCmd" -ForegroundColor Green

if (-not (Test-Command "node")) {
    Write-Host ""
    Write-Host "ERROR: Node.js is not installed." -ForegroundColor Red
    Write-Host "Please install Node.js and re-run setup." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Command "npm")) {
    Write-Host ""
    Write-Host "ERROR: npm is not available." -ForegroundColor Red
    Write-Host "Please install Node.js/npm and re-run setup." -ForegroundColor Yellow
    exit 1
}

Write-Host "Node.js and npm detected." -ForegroundColor Green


# -----------------------------------
# 2. Create required folders
# -----------------------------------

$Folders = @(
    "input",
    "input\processed",
    "output",
    "output\qa_reports",
    "logs"
)

foreach ($folder in $Folders) {
    $fullPath = Join-Path $RepoRoot $folder
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "Created: $folder" -ForegroundColor Green
    } else {
        Write-Host "Exists: $folder" -ForegroundColor DarkGray
    }
}

# -----------------------------------
# 3. Create Python virtual environment
# -----------------------------------

$VenvPath = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Requirements = Join-Path $RepoRoot "requirements.txt"

if (-not (Test-Path $VenvPython)) {
    Write-Host ""
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    & $PythonCmd -m venv $VenvPath
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor DarkGray
}

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip

# Install dependencies
if (Test-Path $Requirements) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    & $VenvPython -m pip install -r $Requirements
} else {
    Write-Host "WARNING: requirements.txt not found." -ForegroundColor Yellow
}

# -----------------------------------
# 4. Install n8n globally if missing
# -----------------------------------

if (-not (Test-Command "n8n")) {
    Write-Host ""
    Write-Host "Installing n8n globally..." -ForegroundColor Cyan
    & npm install -g n8n
} else {
    $version = & n8n --version
    Write-Host "n8n already installed: $version" -ForegroundColor Green
}

# -----------------------------------
# 5. Create .env safely
# -----------------------------------

$EnvExample = Join-Path $RepoRoot ".env.example"
$EnvFile = Join-Path $RepoRoot ".env"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Write-Host ""
        Write-Host "Creating .env from .env.example..." -ForegroundColor Cyan

        # Copy and CLEAN encryption key lines
        $content = Get-Content $EnvExample | Where-Object {
            $_ -notmatch "N8N_ENCRYPTION_KEY"
        }

        $content | Set-Content $EnvFile

        Write-Host ".env created (encryption key removed for local setup)" -ForegroundColor Green
    } else {
        Write-Host "WARNING: .env.example not found." -ForegroundColor Yellow
    }
} else {
    Write-Host ".env already exists." -ForegroundColor DarkGray
}

# -----------------------------------
# DONE
# -----------------------------------

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Next step: run start_automation.bat" -ForegroundColor Cyan
Write-Host ""
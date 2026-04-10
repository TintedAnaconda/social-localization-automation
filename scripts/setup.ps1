# scripts/setup.ps1
# Run from repo root:
# powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

function Write-Step($message) {
    Write-Host ""
    Write-Host "=== $message ===" -ForegroundColor Cyan
}

function Test-CommandExists($command) {
    $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

Write-Step "Checking required tools"

if (-not (Test-CommandExists "git")) {
    Write-Error "Git is not installed or not on PATH. Please install Git first."
}

if (-not (Test-CommandExists "python")) {
    Write-Error "Python is not installed or not on PATH. Please install Python 3.11+ first."
}

if (-not (Test-CommandExists "docker")) {
    Write-Error "Docker is not installed or not on PATH. Please install Docker Desktop first."
}

Write-Host "Git found." -ForegroundColor Green
Write-Host "Python found." -ForegroundColor Green
Write-Host "Docker found." -ForegroundColor Green

Write-Step "Creating standard folders"

$folders = @(
    "input",
    "output",
    "logs",
    "config",
    "templates",
    "n8n",
    "n8n\workflows"
)

foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host "Created $folder"
    }
    else {
        Write-Host "Exists: $folder"
    }
}

Write-Step "Creating Python virtual environment"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Virtual environment created at .venv" -ForegroundColor Green
}
else {
    Write-Host ".venv already exists"
}

Write-Step "Activating virtual environment"

$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "Could not find virtual environment activation script at $venvActivate"
}

. $venvActivate

Write-Step "Upgrading pip and installing Python packages"

python -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
    Write-Host "requirements.txt installed" -ForegroundColor Green
}
else {
    Write-Host "requirements.txt not found yet. Skipping package install." -ForegroundColor Yellow
}

Write-Step "Creating local .env from .env.example"

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example" -ForegroundColor Green
    }
    else {
        Write-Host ".env.example not found. Skipping .env creation." -ForegroundColor Yellow
    }
}
else {
    Write-Host ".env already exists"
}

Write-Step "Checking Docker Compose availability"

try {
    docker compose version | Out-Null
    Write-Host "Docker Compose is available." -ForegroundColor Green
}
catch {
    Write-Error "Docker Compose is not available. Make sure Docker Desktop is installed and running."
}

Write-Step "Pulling n8n image"

if (Test-Path "docker-compose.yml") {
    docker compose pull
    Write-Host "Docker images pulled successfully." -ForegroundColor Green
}
else {
    Write-Host "docker-compose.yml not found yet. Skipping docker pull." -ForegroundColor Yellow
}

Write-Step "Setup complete"

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Open .env and add any required values."
Write-Host "2. Start Docker Desktop if it is not already running."
Write-Host "3. Run: .\scripts\start.ps1"
Write-Host "4. Open n8n at http://localhost:5678"
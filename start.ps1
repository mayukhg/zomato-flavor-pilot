# FlavorPilot Development Server Startup Script (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting FlavorPilot Development Environment..." -ForegroundColor Cyan
Write-Host ""

# Check if PostgreSQL is running
Write-Host "📊 Checking PostgreSQL..." -ForegroundColor Yellow
$pgRunning = $false
try {
    $pgProcess = Get-Process postgres -ErrorAction SilentlyContinue
    if ($pgProcess) {
        $pgRunning = $true
        Write-Host "   ✓ PostgreSQL is running" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  PostgreSQL not found. Please install PostgreSQL 14+ with pgvector extension." -ForegroundColor Red
    Write-Host "   Installation guide: https://www.postgresql.org/download/" -ForegroundColor Yellow
    exit 1
}

# Create database if it doesn't exist
Write-Host "📊 Setting up database..." -ForegroundColor Yellow
$dbExists = & psql -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'flavorpilot'" 2>$null
if (-not $dbExists) {
    & psql -h localhost -U postgres -c "CREATE DATABASE flavorpilot" 2>$null
    Write-Host "   ✓ Database created" -ForegroundColor Green
} else {
    Write-Host "   ✓ Database already exists" -ForegroundColor Green
}

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
& pip install -q -r backend/requirements.txt
Write-Host "   ✓ Python dependencies installed" -ForegroundColor Green

# Generate golden dataset
if (-not (Test-Path "/workspace/scratch/golden_dataset_flavorpilot.json")) {
    Write-Host "🔧 Generating golden dataset..." -ForegroundColor Yellow
    & python seed_data_flavorpilot.py
    Write-Host "   ✓ Golden dataset generated" -ForegroundColor Green
}

# Seed database
Write-Host "🌱 Seeding database..." -ForegroundColor Yellow
& python scripts/seed_database.py
Write-Host "   ✓ Database seeded" -ForegroundColor Green

# Start FastAPI backend in background
Write-Host "🔥 Starting FastAPI backend server..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD/backend
    python -m app.main
}
Write-Host "   ✓ Backend started (Job ID: $($backendJob.Id))" -ForegroundColor Green

# Wait for backend to be ready
Write-Host "⏳ Waiting for backend to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend dev server
Write-Host "⚡ Starting Vite frontend dev server..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    npm run dev
}
Write-Host "   ✓ Frontend started (Job ID: $($frontendJob.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "✅ FlavorPilot is running!" -ForegroundColor Green
Write-Host ""
Write-Host "   Frontend:    " -NoNewline
Write-Host "http://localhost:5173" -ForegroundColor Cyan
Write-Host "   Backend API: " -NoNewline
Write-Host "http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API Docs:    " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend Job ID:  $($backendJob.Id)" -ForegroundColor Gray
Write-Host "Frontend Job ID: $($frontendJob.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop all services, run: " -NoNewline
Write-Host "./stop.ps1" -ForegroundColor Yellow
Write-Host ""

# Store job IDs for cleanup
$backendJob.Id | Out-File -FilePath ".flavorpilot.backend.pid" -Force
$frontendJob.Id | Out-File -FilePath ".flavorpilot.frontend.pid" -Force

Write-Host "Press Ctrl+C to exit (servers will continue running in background)" -ForegroundColor Gray

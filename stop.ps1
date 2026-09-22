# FlavorPilot Development Server Shutdown Script (PowerShell)

$ErrorActionPreference = "Continue"

Write-Host "🛑 Stopping FlavorPilot Development Environment..." -ForegroundColor Cyan
Write-Host ""

$stopped = $false

# Try to stop using stored job IDs first
if (Test-Path ".flavorpilot.backend.pid") {
    $backendJobId = Get-Content ".flavorpilot.backend.pid"
    Write-Host "📊 Stopping FastAPI backend (Job ID: $backendJobId)..." -ForegroundColor Yellow
    try {
        Stop-Job -Id $backendJobId -ErrorAction SilentlyContinue
        Remove-Job -Id $backendJobId -ErrorAction SilentlyContinue
        Remove-Item ".flavorpilot.backend.pid" -Force
        Write-Host "   ✓ Backend stopped" -ForegroundColor Green
        $stopped = $true
    } catch {
        Write-Host "   ℹ️  Backend job not found" -ForegroundColor Gray
    }
}

if (Test-Path ".flavorpilot.frontend.pid") {
    $frontendJobId = Get-Content ".flavorpilot.frontend.pid"
    Write-Host "⚡ Stopping Vite frontend (Job ID: $frontendJobId)..." -ForegroundColor Yellow
    try {
        Stop-Job -Id $frontendJobId -ErrorAction SilentlyContinue
        Remove-Job -Id $frontendJobId -ErrorAction SilentlyContinue
        Remove-Item ".flavorpilot.frontend.pid" -Force
        Write-Host "   ✓ Frontend stopped" -ForegroundColor Green
        $stopped = $true
    } catch {
        Write-Host "   ℹ️  Frontend job not found" -ForegroundColor Gray
    }
}

# Fallback: Kill processes by name
Write-Host "🔍 Checking for remaining processes..." -ForegroundColor Yellow

# Kill Python processes running app.main
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*app.main*"
}
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force
    Write-Host "   ✓ Stopped backend processes" -ForegroundColor Green
    $stopped = $true
}

# Kill Node/Vite processes on port 5173
$frontendProcesses = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess -Unique
if ($frontendProcesses) {
    $frontendProcesses | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "   ✓ Stopped frontend processes" -ForegroundColor Green
    $stopped = $true
}

# Kill backend processes on port 8000
$backendProcesses = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess -Unique
if ($backendProcesses) {
    $backendProcesses | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "   ✓ Stopped backend port 8000 processes" -ForegroundColor Green
    $stopped = $true
}

if (-not $stopped) {
    Write-Host "   ℹ️  No FlavorPilot processes found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ FlavorPilot has been stopped!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Smoke Test Script for Generated Apps (Windows PowerShell)
# ============================================================================
# This script verifies that a generated app starts correctly with docker-compose
# and that all health endpoints respond as expected.
#
# Usage: .\scripts\smoke-test.ps1 [app_directory]
#
# Example:
#   .\scripts\smoke-test.ps1 .\test_apps\phase_c_test
#
# ============================================================================

param(
    [string]$AppDir = ".\generated_app"
)

# Configuration
$TIMEOUT = 120  # Max seconds to wait
$HEALTH_CHECK_INTERVAL = 5
$MAX_HEALTH_CHECKS = [math]::Floor($TIMEOUT / $HEALTH_CHECK_INTERVAL)

# Check if directory exists
if (-not (Test-Path $AppDir)) {
    Write-Host "Error: Directory '$AppDir' not found" -ForegroundColor Red
    Write-Host "Usage: .\smoke-test.ps1 [app_directory]"
    exit 1
}

Push-Location $AppDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🧪 Smoke Test for: $(Split-Path $AppDir -Leaf)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Cleanup function
function Cleanup {
    Write-Host "`nCleaning up..." -ForegroundColor Yellow
    docker compose down --volumes --remove-orphans 2>$null
}

# Register cleanup on script exit
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

try {
    # Step 1: Verify required files
    Write-Host "`nStep 1: Verifying required files..." -ForegroundColor Yellow
    
    $requiredFiles = @(
        "docker-compose.yml",
        ".env",
        "backend\Dockerfile",
        "frontend\Dockerfile",
        "backend\app\main.py"
    )
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Host "  ✓ $file" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $file (MISSING)" -ForegroundColor Red
            exit 1
        }
    }
    
    # Step 2: Start containers
    Write-Host "`nStep 2: Starting docker-compose..." -ForegroundColor Yellow
    docker compose up -d --build
    
    # Step 3: Wait for backend health
    Write-Host "`nStep 3: Waiting for services to be healthy..." -ForegroundColor Yellow
    Write-Host "  Waiting for backend..."
    
    $backendReady = $false
    for ($i = 1; $i -le $MAX_HEALTH_CHECKS; $i++) {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.status -eq "healthy") {
                $backendReady = $true
                Write-Host "  ✓ Backend is healthy" -ForegroundColor Green
                break
            }
        } catch {
            # Ignore errors, just retry
        }
        Write-Host "    Attempt $i/$MAX_HEALTH_CHECKS..."
        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL
    }
    
    if (-not $backendReady) {
        Write-Host "  ✗ Backend failed to start" -ForegroundColor Red
        Write-Host "`nBackend logs:" -ForegroundColor Yellow
        docker compose logs backend --tail=50
        exit 1
    }
    
    # Step 4: Test health endpoints
    Write-Host "`nStep 4: Testing health endpoints..." -ForegroundColor Yellow
    
    # Test /health
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
    if ($response.status -eq "healthy") {
        Write-Host "  ✓ /health - OK" -ForegroundColor Green
    } else {
        Write-Host "  ✗ /health - FAILED" -ForegroundColor Red
        exit 1
    }
    
    # Test /health/ready
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health/ready" -Method Get
    if ($response.status -eq "ready") {
        Write-Host "  ✓ /health/ready - OK (DB connected)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ /health/ready - FAILED" -ForegroundColor Red
        exit 1
    }
    
    # Test /health/live
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health/live" -Method Get
    if ($response.status -eq "alive") {
        Write-Host "  ✓ /health/live - OK" -ForegroundColor Green
    } else {
        Write-Host "  ✗ /health/live - FAILED" -ForegroundColor Red
        exit 1
    }
    
    # Step 5: Summary
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "✅ SMOKE TEST PASSED" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Services running:"
    Write-Host "  - Backend API: http://localhost:8000"
    Write-Host "  - API Docs:    http://localhost:8000/docs"
    Write-Host "  - Frontend:    http://localhost:3000"
    Write-Host ""
    Write-Host "To stop services: docker compose down"
    Write-Host ""
    
} finally {
    Pop-Location
}

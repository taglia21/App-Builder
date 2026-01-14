@echo off
echo 🚀 Starting AI-PoweredCrmAutomation...

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Docker is not installed.
    pause
    exit /b 1
)

echo Building and starting containers...
docker-compose up --build

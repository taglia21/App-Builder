#!/bin/bash
echo "🚀 Starting AI-PoweredCrmAutomation..."

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed."
    exit 1
fi

echo "Building and starting containers..."
docker-compose up --build

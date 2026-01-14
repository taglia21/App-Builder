#!/bin/bash
# ============================================================================
# Smoke Test Script for Generated Apps
# ============================================================================
# This script verifies that a generated app starts correctly with docker-compose
# and that all health endpoints respond as expected.
#
# Usage: ./scripts/smoke-test.sh [app_directory]
#
# Example:
#   ./scripts/smoke-test.sh ./test_apps/phase_c_test
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=120  # Max seconds to wait for services
HEALTH_CHECK_INTERVAL=5
MAX_HEALTH_CHECKS=$((TIMEOUT / HEALTH_CHECK_INTERVAL))

# Get app directory
APP_DIR="${1:-./generated_app}"

if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Error: Directory '$APP_DIR' not found${NC}"
    echo "Usage: $0 [app_directory]"
    exit 1
fi

cd "$APP_DIR"

echo "============================================================"
echo "🧪 Smoke Test for: $(basename "$APP_DIR")"
echo "============================================================"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker compose down --volumes --remove-orphans 2>/dev/null || true
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Step 1: Verify required files exist
echo -e "\n${YELLOW}Step 1: Verifying required files...${NC}"

required_files=(
    "docker-compose.yml"
    ".env"
    "backend/Dockerfile"
    "frontend/Dockerfile"
    "backend/app/main.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ✓ $file"
    else
        echo -e "  ${RED}✗ $file (MISSING)${NC}"
        exit 1
    fi
done

# Step 2: Build and start containers
echo -e "\n${YELLOW}Step 2: Starting docker-compose...${NC}"
docker compose up -d --build

# Step 3: Wait for health checks
echo -e "\n${YELLOW}Step 3: Waiting for services to be healthy...${NC}"

check_health() {
    local url=$1
    local expected=$2
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$response" == "$expected" ]; then
        return 0
    else
        return 1
    fi
}

# Wait for backend health
echo "  Waiting for backend..."
backend_ready=false
for i in $(seq 1 $MAX_HEALTH_CHECKS); do
    if check_health "http://localhost:8000/health" "200"; then
        backend_ready=true
        echo -e "  ${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    echo "    Attempt $i/$MAX_HEALTH_CHECKS..."
    sleep $HEALTH_CHECK_INTERVAL
done

if [ "$backend_ready" != "true" ]; then
    echo -e "  ${RED}✗ Backend failed to start${NC}"
    echo -e "\n${YELLOW}Backend logs:${NC}"
    docker compose logs backend --tail=50
    exit 1
fi

# Step 4: Test health endpoints
echo -e "\n${YELLOW}Step 4: Testing health endpoints...${NC}"

# Test /health
response=$(curl -s "http://localhost:8000/health")
if echo "$response" | grep -q "healthy"; then
    echo -e "  ${GREEN}✓ /health - OK${NC}"
else
    echo -e "  ${RED}✗ /health - FAILED${NC}"
    echo "  Response: $response"
    exit 1
fi

# Test /health/ready (should have DB connected)
response=$(curl -s "http://localhost:8000/health/ready")
if echo "$response" | grep -q "ready"; then
    echo -e "  ${GREEN}✓ /health/ready - OK (DB connected)${NC}"
else
    echo -e "  ${RED}✗ /health/ready - FAILED${NC}"
    echo "  Response: $response"
    exit 1
fi

# Test /health/live
response=$(curl -s "http://localhost:8000/health/live")
if echo "$response" | grep -q "alive"; then
    echo -e "  ${GREEN}✓ /health/live - OK${NC}"
else
    echo -e "  ${RED}✗ /health/live - FAILED${NC}"
    echo "  Response: $response"
    exit 1
fi

# Step 5: Test API docs
echo -e "\n${YELLOW}Step 5: Testing API documentation...${NC}"

if check_health "http://localhost:8000/docs" "200"; then
    echo -e "  ${GREEN}✓ /docs - OpenAPI docs available${NC}"
else
    echo -e "  ${YELLOW}⚠ /docs - Not accessible (non-critical)${NC}"
fi

# Step 6: Test frontend (if available)
echo -e "\n${YELLOW}Step 6: Testing frontend...${NC}"

frontend_ready=false
for i in $(seq 1 10); do
    if check_health "http://localhost:3000" "200"; then
        frontend_ready=true
        echo -e "  ${GREEN}✓ Frontend is running${NC}"
        break
    fi
    sleep 3
done

if [ "$frontend_ready" != "true" ]; then
    echo -e "  ${YELLOW}⚠ Frontend not ready (may still be building)${NC}"
fi

# Step 7: Summary
echo -e "\n============================================================"
echo -e "${GREEN}✅ SMOKE TEST PASSED${NC}"
echo "============================================================"
echo ""
echo "Services running:"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs:    http://localhost:8000/docs"
echo "  - Frontend:    http://localhost:3000"
echo ""
echo "Health endpoints:"
echo "  - /health       - Basic liveness"
echo "  - /health/ready - DB connectivity check"  
echo "  - /health/live  - Kubernetes probe"
echo ""
echo "To stop services: docker compose down"
echo ""

exit 0

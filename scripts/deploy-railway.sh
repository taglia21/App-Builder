#!/bin/bash
# Railway Deployment Test Script
# Tests that the dashboard can run with minimal dependencies

set -e

echo "=========================================="
echo "Railway Deployment Test"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not in a virtual environment${NC}"
    echo "Creating temporary test environment..."
    python -m venv .venv-railway-test
    source .venv-railway-test/bin/activate
    CLEANUP_VENV=1
fi

echo ""
echo "Step 1: Installing minimal requirements..."
echo "----------------------------------------"
pip install -r requirements-railway.txt --quiet

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to install requirements${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Requirements installed successfully${NC}"

echo ""
echo "Step 2: Testing imports..."
echo "----------------------------------------"
python -c "
from src.dashboard.app import app
print('✓ Dashboard app imports successfully')
"

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to import dashboard app${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Imports successful${NC}"

echo ""
echo "Step 3: Starting dashboard server..."
echo "----------------------------------------"
export PORT=8000
export ENVIRONMENT=testing
export SECRET_KEY=test-secret-key-for-local-testing
export STRIPE_SECRET_KEY=sk_test_dummy
export RESEND_API_KEY=re_dummy

# Start server in background
python -m uvicorn src.dashboard.app:app --host 0.0.0.0 --port $PORT &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

echo ""
echo "Step 4: Testing endpoints..."
echo "----------------------------------------"

# Test health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:$PORT/health)
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✓ Health endpoint: $HEALTH_RESPONSE${NC}"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Test root endpoint
ROOT_RESPONSE=$(curl -s http://localhost:$PORT/)
if echo "$ROOT_RESPONSE" | grep -q "status\|LaunchForge"; then
    echo -e "${GREEN}✓ Root endpoint: $ROOT_RESPONSE${NC}"
else
    echo -e "${YELLOW}⚠ Root endpoint returned: $ROOT_RESPONSE${NC}"
fi

# Test that server responds to HTTP
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/)
echo "HTTP Response Code: $HTTP_CODE"

echo ""
echo "Step 5: Cleanup..."
echo "----------------------------------------"

# Stop server
kill $SERVER_PID 2>/dev/null
echo "Server stopped"

# Cleanup virtual environment if we created it
if [ "$CLEANUP_VENV" = "1" ]; then
    deactivate 2>/dev/null
    rm -rf .venv-railway-test
    echo "Temporary environment removed"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment test PASSED!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Commit all changes: git add -A && git commit -m 'Railway deployment fix'"
echo "2. Push to GitHub: git push origin main"
echo "3. Deploy to Railway: railway up"
echo ""
echo "Or try alternative platforms - see docs/DEPLOYMENT_ALTERNATIVES.md"

#!/bin/bash
# One-Click Deployment Script for Generated Apps
# Supports: Render, Railway, Vercel, and Docker
#
# Usage: ./deploy.sh [target] [options]
#   Targets: render, railway, vercel, docker, all
#   Options: --skip-frontend, --skip-backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="${APP_DIR:-$(pwd)}"
DEPLOY_TARGET="${1:-render}"
SKIP_FRONTEND=false
SKIP_BACKEND=false

# Parse options
for arg in "$@"; do
    case $arg in
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --skip-backend)
            SKIP_BACKEND=true
            shift
            ;;
    esac
done

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      🚀 One-Click Deployment for Generated Apps             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check for required tools
    if [ "$DEPLOY_TARGET" = "render" ]; then
        if ! command -v curl &> /dev/null; then
            echo -e "${RED}Error: curl is required for Render deployment${NC}"
            exit 1
        fi
    fi
    
    if [ "$DEPLOY_TARGET" = "railway" ]; then
        if ! command -v railway &> /dev/null; then
            echo -e "${YELLOW}Railway CLI not found. Installing...${NC}"
            npm install -g @railway/cli
        fi
    fi
    
    if [ "$DEPLOY_TARGET" = "vercel" ]; then
        if ! command -v vercel &> /dev/null; then
            echo -e "${YELLOW}Vercel CLI not found. Installing...${NC}"
            npm install -g vercel
        fi
    fi
    
    if [ "$DEPLOY_TARGET" = "docker" ]; then
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}Error: Docker is required for container deployment${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Prerequisites check passed${NC}"
}

# Deploy to Render
deploy_render() {
    echo -e "${BLUE}Deploying to Render...${NC}"
    
    if [ ! -f "$APP_DIR/render.yaml" ]; then
        echo -e "${YELLOW}Creating render.yaml...${NC}"
        cat > "$APP_DIR/render.yaml" << 'EOF'
services:
  - type: web
    name: backend
    env: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: postgres
          property: connectionString
      - key: SECRET_KEY
        generateValue: true

  - type: web
    name: frontend
    env: static
    buildCommand: cd frontend && npm install && npm run build
    staticPublishPath: frontend/out
    envVars:
      - key: NEXT_PUBLIC_API_URL
        value: https://backend.onrender.com

databases:
  - name: postgres
    plan: free
EOF
    fi
    
    echo -e "${GREEN}✓ render.yaml created${NC}"
    echo ""
    echo -e "${YELLOW}To complete Render deployment:${NC}"
    echo "1. Go to https://render.com/deploy"
    echo "2. Connect your GitHub repository"
    echo "3. Render will auto-detect the render.yaml configuration"
    echo ""
    echo -e "${BLUE}Or use the Render CLI:${NC}"
    echo "  render blueprint apply"
}

# Deploy to Railway
deploy_railway() {
    echo -e "${BLUE}Deploying to Railway...${NC}"
    
    # Check if logged in
    if ! railway whoami &> /dev/null; then
        echo -e "${YELLOW}Please log in to Railway:${NC}"
        railway login
    fi
    
    # Initialize project if not exists
    if [ ! -f "$APP_DIR/.railway" ]; then
        echo -e "${YELLOW}Initializing Railway project...${NC}"
        cd "$APP_DIR"
        railway init
    fi
    
    # Deploy backend
    if [ "$SKIP_BACKEND" = false ]; then
        echo -e "${BLUE}Deploying backend...${NC}"
        cd "$APP_DIR/backend"
        
        # Create railway.json for backend
        cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
EOF
        
        railway up
        cd "$APP_DIR"
    fi
    
    # Deploy frontend
    if [ "$SKIP_FRONTEND" = false ]; then
        echo -e "${BLUE}Deploying frontend...${NC}"
        cd "$APP_DIR/frontend"
        
        cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "npm install && npm run build"
  },
  "deploy": {
    "startCommand": "npm start"
  }
}
EOF
        
        railway up
        cd "$APP_DIR"
    fi
    
    echo -e "${GREEN}✓ Railway deployment complete${NC}"
    echo ""
    railway domain
}

# Deploy to Vercel
deploy_vercel() {
    echo -e "${BLUE}Deploying to Vercel...${NC}"
    
    if [ "$SKIP_FRONTEND" = false ]; then
        cd "$APP_DIR/frontend"
        
        # Check if logged in
        if ! vercel whoami &> /dev/null; then
            echo -e "${YELLOW}Please log in to Vercel:${NC}"
            vercel login
        fi
        
        # Create vercel.json if not exists
        if [ ! -f "vercel.json" ]; then
            cat > vercel.json << 'EOF'
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "@backend_url"
  }
}
EOF
        fi
        
        echo -e "${YELLOW}Deploying frontend to Vercel...${NC}"
        vercel --prod
        
        cd "$APP_DIR"
    fi
    
    if [ "$SKIP_BACKEND" = false ]; then
        echo ""
        echo -e "${YELLOW}Note: For backend deployment, consider:${NC}"
        echo "  - Vercel Serverless Functions (for API routes)"
        echo "  - Railway/Render (for full Python backend)"
        echo "  - AWS Lambda with API Gateway"
    fi
    
    echo -e "${GREEN}✓ Vercel deployment complete${NC}"
}

# Deploy with Docker
deploy_docker() {
    echo -e "${BLUE}Building and running with Docker...${NC}"
    
    cd "$APP_DIR"
    
    # Check if docker-compose.yml exists
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}Error: docker-compose.yml not found${NC}"
        exit 1
    fi
    
    # Build and run
    echo -e "${YELLOW}Building containers...${NC}"
    docker compose build
    
    echo -e "${YELLOW}Starting services...${NC}"
    docker compose up -d
    
    echo ""
    echo -e "${GREEN}✓ Docker deployment complete${NC}"
    echo ""
    echo -e "${BLUE}Services running:${NC}"
    docker compose ps
    echo ""
    echo -e "Frontend: ${GREEN}http://localhost:3000${NC}"
    echo -e "Backend:  ${GREEN}http://localhost:8000${NC}"
    echo -e "API Docs: ${GREEN}http://localhost:8000/docs${NC}"
}

# Deploy to all platforms
deploy_all() {
    echo -e "${YELLOW}Preparing for multi-platform deployment...${NC}"
    
    deploy_docker
    echo ""
    deploy_render
    echo ""
    echo -e "${YELLOW}For Railway and Vercel, run separately:${NC}"
    echo "  ./deploy.sh railway"
    echo "  ./deploy.sh vercel"
}

# Main execution
main() {
    check_prerequisites
    
    case "$DEPLOY_TARGET" in
        render)
            deploy_render
            ;;
        railway)
            deploy_railway
            ;;
        vercel)
            deploy_vercel
            ;;
        docker)
            deploy_docker
            ;;
        all)
            deploy_all
            ;;
        *)
            echo -e "${RED}Unknown deployment target: $DEPLOY_TARGET${NC}"
            echo ""
            echo "Usage: ./deploy.sh [target] [options]"
            echo ""
            echo "Targets:"
            echo "  render   - Deploy to Render.com"
            echo "  railway  - Deploy to Railway.app"
            echo "  vercel   - Deploy to Vercel (frontend)"
            echo "  docker   - Build and run with Docker"
            echo "  all      - Prepare for all platforms"
            echo ""
            echo "Options:"
            echo "  --skip-frontend  Skip frontend deployment"
            echo "  --skip-backend   Skip backend deployment"
            exit 1
            ;;
    esac
}

main

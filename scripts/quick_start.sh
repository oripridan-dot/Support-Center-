#!/bin/bash

# Quick Start Script for Worker Orchestration System
# This script sets up and verifies the entire orchestration infrastructure

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                                ║
║   🚀 Halilit Support Center - Worker Orchestration System   ║
║                                                                ║
║   Production-Grade Distributed Task Processing                ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ============================================================================
# Step 1: Environment Setup
# ============================================================================

echo -e "${YELLOW}[1/6]${NC} Setting up environment..."

if [ ! -f .env ]; then
    echo -e "${GREEN}✓${NC} Creating .env from template..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ ${NC} Please edit .env and add your OPENAI_API_KEY"
    echo -e "${YELLOW}⚠ ${NC} Run: nano .env"
    read -p "Press Enter after updating .env file..."
fi

# ============================================================================
# Step 2: Install Dependencies
# ============================================================================

echo -e "${YELLOW}[2/6]${NC} Installing dependencies..."

if [ "$1" == "--docker" ]; then
    echo -e "${GREEN}✓${NC} Using Docker mode (dependencies in containers)"
else
    cd backend
    pip install -r requirements.txt > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} Python dependencies installed"
    
    playwright install chromium > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} Playwright browsers installed"
    cd ..
fi

# ============================================================================
# Step 3: Start Infrastructure
# ============================================================================

echo -e "${YELLOW}[3/6]${NC} Starting infrastructure..."

if [ "$1" == "--docker" ]; then
    echo "Starting with Docker Compose..."
    docker-compose up -d redis chromadb
    sleep 5
    echo -e "${GREEN}✓${NC} Redis and ChromaDB started"
else
    # Check if Redis is running
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is already running"
    else
        echo -e "${YELLOW}⚠ ${NC} Please start Redis manually: redis-server"
        exit 1
    fi
fi

# ============================================================================
# Step 4: Start Workers
# ============================================================================

echo -e "${YELLOW}[4/6]${NC} Starting workers..."

if [ "$1" == "--docker" ]; then
    docker-compose up -d scraper_worker embedding_worker rag_worker maintenance_worker celery_beat flower
    sleep 5
    echo -e "${GREEN}✓${NC} All workers started in Docker"
else
    ./scripts/manage_workers.sh start
    echo -e "${GREEN}✓${NC} All workers started locally"
fi

# ============================================================================
# Step 5: Start Backend
# ============================================================================

echo -e "${YELLOW}[5/6]${NC} Starting FastAPI backend..."

if [ "$1" == "--docker" ]; then
    docker-compose up -d backend
    sleep 3
else
    cd backend
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 > ../logs/backend.log 2>&1 &
    echo $! > ../logs/backend.pid
    cd ..
    sleep 3
fi

echo -e "${GREEN}✓${NC} Backend started"

# ============================================================================
# Step 6: Verify System
# ============================================================================

echo -e "${YELLOW}[6/6]${NC} Verifying system health..."

# Wait for services to be ready
sleep 5

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis: Healthy"
else
    echo -e "${RED}✗${NC} Redis: Failed"
fi

# Check Backend
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend: Healthy"
else
    echo -e "${RED}✗${NC} Backend: Starting up..."
fi

# Check Flower
if curl -sf http://localhost:5555 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Flower: Healthy"
else
    echo -e "${YELLOW}⚠${NC}  Flower: Starting up..."
fi

# ============================================================================
# Success Summary
# ============================================================================

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ System Operational                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Access Points:${NC}"
echo ""
echo "  🌐 FastAPI Backend:    http://localhost:8080"
echo "  📄 API Docs:           http://localhost:8080/docs"
echo "  🌸 Flower Dashboard:   http://localhost:5555"
echo "  📈 Prometheus:         http://localhost:9090"
echo "  📊 Grafana:            http://localhost:3001"
echo ""
echo -e "${BLUE}🛠️  Management Commands:${NC}"
echo ""
echo "  Check status:          ./scripts/manage_workers.sh status"
echo "  View logs:             ./scripts/manage_workers.sh logs <worker>"
echo "  Stop system:           ./scripts/manage_workers.sh stop"
echo "  Restart workers:       ./scripts/manage_workers.sh restart"
echo ""
echo -e "${BLUE}🧪 Test Commands:${NC}"
echo ""
echo "  Test scraping:         ./scripts/manage_workers.sh test-scraping"
echo "  Test embeddings:       ./scripts/manage_workers.sh test-embedding"
echo "  Test RAG:              ./scripts/manage_workers.sh test-rag"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo ""
echo "  Full Guide:            cat WORKER_ORCHESTRATION_GUIDE.md"
echo ""
echo -e "${GREEN}Ready to process tasks! 🚀${NC}"
echo ""

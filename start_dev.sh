#!/bin/bash

# High-Performance Worker System - Startup Script
# Starts backend and frontend with proper configuration

set -e

echo "🚀 Starting Halilit Support Center with High-Performance Workers"
echo "================================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Kill existing processes
echo -e "${YELLOW}Stopping existing processes...${NC}"
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "vite" 2>/dev/null || true
fuser -k 8080/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 3001/tcp 2>/dev/null || true
sleep 2

# Start Backend
echo -e "${BLUE}Starting Backend (Port 8080)...${NC}"
cd /workspaces/Support-Center-/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8080/api/workers/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend started successfully${NC}"
        break
    fi
    sleep 1
done

# Check backend health
HEALTH=$(curl -s http://localhost:8080/api/workers/health)
if echo "$HEALTH" | grep -q "healthy"; then
    WORKERS=$(echo "$HEALTH" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_workers'])")
    echo -e "${GREEN}✓ Backend healthy with $WORKERS workers${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check failed${NC}"
fi

# Start Frontend
echo -e "${BLUE}Starting Frontend (Port 3000)...${NC}"
cd /workspaces/Support-Center-/frontend
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend to start..."
sleep 8

echo ""
echo "================================================================"
echo -e "${GREEN}🎉 All Services Started!${NC}"
echo "================================================================"
echo ""
echo -e "📡 Backend API:  ${BLUE}http://localhost:8080${NC}"
echo -e "   Health:       http://localhost:8080/api/workers/health"
echo -e "   Metrics:      http://localhost:8080/api/workers/metrics"
echo -e "   API Docs:     http://localhost:8080/docs"
echo ""
echo -e "🌐 Frontend UI:  ${BLUE}http://localhost:3000${NC} (or 3001 if 3000 in use)"
echo -e "   Home:         http://localhost:3000/"
echo -e "   Performance:  http://localhost:3000/performance"
echo -e "   Workers:      http://localhost:3000/workers"
echo ""
echo -e "📊 High-Performance Monitoring: ${BLUE}http://localhost:3000/performance${NC}"
echo ""
echo "================================================================"
echo -e "${YELLOW}Logs:${NC}"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "To stop services:"
echo "   pkill -f uvicorn"
echo "   pkill -f vite"
echo "================================================================"
echo ""

# Keep script running and show live backend status
echo "Monitoring backend status (Ctrl+C to exit)..."
echo ""

while true; do
    if curl -s http://localhost:8080/api/workers/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:8080/api/workers/health)
        STATUS=$(echo "$HEALTH" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"{d['status']}: {d['total_processed']} processed, {d['total_failed']} failed\")" 2>/dev/null || echo "Running")
        echo -e "\r${GREEN}✓${NC} Backend: $STATUS    " | tr -d '\n'
    else
        echo -e "\r${YELLOW}⚠${NC} Backend: Not responding    " | tr -d '\n'
    fi
    sleep 5
done

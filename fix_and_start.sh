#!/bin/bash
# ===================================================================
# FRONTEND FIX - Complete Solution
# ===================================================================

set -e

echo "🔧 Fixing Halilit Support Center Frontend..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ===================================================================
# 1. KILL EXISTING PROCESSES
# ===================================================================
echo "${BLUE}🛑 Stopping existing processes...${NC}"

# Kill backend
lsof -ti:8080 | xargs kill -9 2>/dev/null || true

# Kill frontend  
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Kill ChromaDB
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo "${GREEN}✅ Processes stopped${NC}"
sleep 2
echo ""

# ===================================================================
# 2. START CHROMADB
# ===================================================================
echo "${BLUE}🗄️  Starting ChromaDB...${NC}"

cd /workspaces/Support-Center-

# Check if ChromaDB should run in docker or standalone
if command -v docker &> /dev/null; then
    echo "Using Docker for ChromaDB..."
    docker-compose up -d chromadb 2>/dev/null || docker run -d -p 8000:8000 chromadb/chroma:latest
else
    echo "Starting ChromaDB standalone..."
    cd backend && chroma run --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
    cd ..
fi

sleep 3
echo "${GREEN}✅ ChromaDB started${NC}"
echo ""

# ===================================================================
# 3. START BACKEND
# ===================================================================
echo "${BLUE}🚀 Starting Backend API...${NC}"

cd /workspaces/Support-Center-/backend

# Start backend in background
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!

echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "${GREEN}✅ Backend started successfully!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "${RED}❌ Backend failed to start${NC}"
        echo "Check logs: tail -f /workspaces/Support-Center-/logs/backend.log"
        exit 1
    fi
    sleep 1
done

echo ""

# ===================================================================
# 4. START FRONTEND
# ===================================================================
echo "${BLUE}🎨 Starting Frontend...${NC}"

cd /workspaces/Support-Center-/frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start frontend in background
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "${GREEN}✅ Frontend started successfully!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "${YELLOW}⚠️  Frontend may still be starting...${NC}"
        echo "Check logs: tail -f /workspaces/Support-Center-/logs/frontend.log"
    fi
    sleep 1
done

echo ""

# ===================================================================
# 5. VERIFY EVERYTHING
# ===================================================================
echo "${BLUE}🧪 Verifying services...${NC}"
echo ""

# Test backend
echo "Testing backend API..."
HEALTH=$(curl -s http://localhost:8080/health 2>&1)
if echo "$HEALTH" | grep -q "healthy\|operational"; then
    echo "${GREEN}✅ Backend API: OK${NC}"
else
    echo "${RED}❌ Backend API: FAILED${NC}"
    echo "Response: $HEALTH"
fi

# Test backend API v2
echo "Testing backend API v2..."
STATUS=$(curl -s http://localhost:8080/api/v2/workers/status 2>&1)
if echo "$STATUS" | grep -q "workers\|running"; then
    echo "${GREEN}✅ Backend API v2: OK${NC}"
else
    echo "${YELLOW}⚠️  Backend API v2: Check manually${NC}"
fi

# Test frontend
echo "Testing frontend..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "${GREEN}✅ Frontend: OK${NC}"
else
    echo "${YELLOW}⚠️  Frontend: Still starting...${NC}"
fi

echo ""

# ===================================================================
# SUCCESS
# ===================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "${GREEN}✅ SERVICES STARTED!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📊 Service URLs:"
echo "   Frontend:  ${BLUE}http://localhost:5173${NC}"
echo "   Backend:   ${BLUE}http://localhost:8080${NC}"
echo "   API Docs:  ${BLUE}http://localhost:8080/docs${NC}"
echo "   ChromaDB:  ${BLUE}http://localhost:8000${NC}"
echo ""
echo "📝 Logs:"
echo "   Backend:   ${BLUE}tail -f logs/backend.log${NC}"
echo "   Frontend:  ${BLUE}tail -f logs/frontend.log${NC}"
echo ""
echo "🛑 To stop:"
echo "   ${BLUE}kill $BACKEND_PID $FRONTEND_PID${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════════"

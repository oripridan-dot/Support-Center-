#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   Halilit Support Center - Dev Container Launcher ${NC}"
echo -e "${BLUE}==============================================${NC}"

# 1. Check if servers are already running
echo -e "\n${GREEN}[1/3] Checking for existing processes...${NC}"
BACKEND_RUNNING=$(lsof -ti :8000 2>/dev/null)
FRONTEND_RUNNING=$(lsof -ti :3000 2>/dev/null)

if [ ! -z "$BACKEND_RUNNING" ]; then
    echo -e "${YELLOW}⚠️  Backend already running on port 8000 (PID: $BACKEND_RUNNING)${NC}"
    echo "Stopping existing backend..."
    kill $BACKEND_RUNNING
    sleep 2
fi

if [ ! -z "$FRONTEND_RUNNING" ]; then
    echo -e "${YELLOW}⚠️  Frontend already running on port 5173 (PID: $FRONTEND_RUNNING)${NC}"
    echo "Stopping existing frontend..."
    kill $FRONTEND_RUNNING
    sleep 2
fi

# 2. Start Backend
echo -e "\n${GREEN}[2/3] Starting Backend Server...${NC}"
cd /workspaces/Support-Center-/backend
PYTHONPATH=. nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend starting with PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/brands/stats > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start. Check logs/backend.log${NC}"
        exit 1
    fi
    sleep 1
done

# 3. Start Frontend
echo -e "\n${GREEN}[3/3] Starting Frontend Server...${NC}"
cd /workspaces/Support-Center-/frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend starting with PID: $FRONTEND_PID"

# Wait for frontend to be ready
echo "Waiting for frontend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  Frontend may still be starting. Check logs/frontend.log${NC}"
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}=========================================="
echo "✅ SERVERS STARTED SUCCESSFULLY"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}🌐 Access Points:${NC}"
echo "   Backend  (API):  http://localhost:8000"
echo "   Frontend (UI):   http://localhost:3000"
echo "   API Docs:        http://localhost:8000/docs"
echo "   Health Check:    http://localhost:8000/api/v1/health"
echo ""
echo -e "${BLUE}📊 Process IDs:${NC}"
echo "   Backend  PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo "   Backend:  tail -f /workspaces/Support-Center-/backend/logs/backend.log"
echo "   Frontend: tail -f /workspaces/Support-Center-/logs/frontend.log"
echo ""
echo -e "${BLUE}🛑 To stop servers:${NC}"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   Or run: pkill -f uvicorn; pkill -f vite"
echo ""
echo -e "${GREEN}=========================================="
echo "Happy Coding! 🎵"
echo "==========================================${NC}"

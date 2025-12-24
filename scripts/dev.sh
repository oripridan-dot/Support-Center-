#!/bin/bash
# Development Workflow Manager
# Starts all services with hot reload for streamlined development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log files
BACKEND_LOG="/tmp/backend_dev.log"
FRONTEND_LOG="/tmp/frontend_dev.log"
INGESTION_LOG="/tmp/continuous_ingestion.log"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}        ${GREEN}🎵  Halilit Support Center - Dev Mode  🎵${NC}         ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    pkill -P $$ || true
    pkill -f "uvicorn.*8000" || true
    pkill -f "next dev" || true
    pkill -f "continuous_ingestion" || true
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Check if ports are available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port is in use, cleaning up...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

echo -e "${BLUE}🔍 Checking ports...${NC}"
check_port 8000
check_port 3000
echo -e "${GREEN}✅ Ports are ready${NC}"
echo ""

# Start Backend (FastAPI with auto-reload)
echo -e "${BLUE}🚀 Starting Backend (FastAPI)...${NC}"
cd "$PROJECT_ROOT/backend"
PYTHONPATH=. python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir app \
    > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

sleep 3
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Backend running on http://0.0.0.0:8000 (PID: $BACKEND_PID)${NC}"
    echo -e "   Log: ${BACKEND_LOG}"
else
    echo -e "${RED}❌ Backend failed to start. Check ${BACKEND_LOG}${NC}"
    tail -20 "$BACKEND_LOG"
    exit 1
fi
echo ""

# Start Frontend (Next.js with Turbopack hot reload)
echo -e "${BLUE}🚀 Starting Frontend (Next.js)...${NC}"
cd "$PROJECT_ROOT/frontend"
rm -f .next/dev/lock
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

sleep 5
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Frontend running on http://localhost:3000 (PID: $FRONTEND_PID)${NC}"
    echo -e "   Log: ${FRONTEND_LOG}"
else
    echo -e "${RED}❌ Frontend failed to start. Check ${FRONTEND_LOG}${NC}"
    tail -20 "$FRONTEND_LOG"
    exit 1
fi
echo ""

# Start Continuous Ingestion Service (Optional)
read -p "Start continuous ingestion service? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🚀 Starting Ingestion Service...${NC}"
    cd "$PROJECT_ROOT/backend"
    python scripts/continuous_ingestion.py > "$INGESTION_LOG" 2>&1 &
    INGESTION_PID=$!
    
    sleep 3
    if kill -0 $INGESTION_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Ingestion service running (PID: $INGESTION_PID)${NC}"
        echo -e "   Log: ${INGESTION_LOG}"
    else
        echo -e "${YELLOW}⚠️  Ingestion service failed to start (optional)${NC}"
    fi
    echo ""
fi

# Display status
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                    ${GREEN}ALL SYSTEMS READY!${NC}                     ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}🌐 Frontend:${NC}  http://localhost:3000"
echo -e "${GREEN}🔌 Backend:${NC}   http://0.0.0.0:8000"
echo -e "${GREEN}📚 API Docs:${NC}  http://0.0.0.0:8000/docs"
echo ""
echo -e "${BLUE}🔥 Hot Reload Enabled:${NC}"
echo -e "   • Backend: Changes in ${YELLOW}backend/app/${NC} auto-reload"
echo -e "   • Frontend: Changes auto-reload with Turbopack"
echo ""
echo -e "${YELLOW}📝 Log Files:${NC}"
echo -e "   • Backend:  tail -f ${BACKEND_LOG}"
echo -e "   • Frontend: tail -f ${FRONTEND_LOG}"
[[ ! -z "$INGESTION_PID" ]] && echo -e "   • Ingestion: tail -f ${INGESTION_LOG}"
echo ""
echo -e "${RED}Press Ctrl+C to stop all services${NC}"
echo ""

# Monitor services
while true; do
    sleep 5
    
    # Check if processes are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}❌ Backend crashed! Check logs: ${BACKEND_LOG}${NC}"
        tail -20 "$BACKEND_LOG"
        break
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${RED}❌ Frontend crashed! Check logs: ${FRONTEND_LOG}${NC}"
        tail -20 "$FRONTEND_LOG"
        break
    fi
done

# Wait for user interrupt
wait

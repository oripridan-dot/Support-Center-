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
WORKER_LOG="/tmp/worker.log"

# Parse command line arguments
START_WORKER=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --worker)
            START_WORKER=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

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
    pkill -f "vite.*3000" || true
    pkill -f "python.*worker.py" || true
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
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --reload-dir app \
    > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

sleep 3
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Backend running on http://127.0.0.1:8000 (PID: $BACKEND_PID)${NC}"
    echo -e "   Log: ${BACKEND_LOG}"
else
    echo -e "${RED}❌ Backend failed to start. Check ${BACKEND_LOG}${NC}"
    tail -20 "$BACKEND_LOG"
    exit 1
fi
echo ""

# Start Frontend (Vite with instant HMR)
echo -e "${BLUE}🚀 Starting Frontend (Vite + React)...${NC}"
cd "$PROJECT_ROOT/frontend"
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

# Start Scraper Worker (optional)
if [ "$START_WORKER" = true ]; then
    echo -e "${BLUE}🚀 Starting Scraper Worker...${NC}"
    cd "$PROJECT_ROOT/backend"
    PYTHONPATH=. python worker.py --mode continuous --delay 60 > "$WORKER_LOG" 2>&1 &
    WORKER_PID=$!
    
    sleep 2
    if kill -0 $WORKER_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Worker running (PID: $WORKER_PID)${NC}"
        echo -e "   Log: ${WORKER_LOG}"
    else
        echo -e "${YELLOW}⚠️  Worker failed to start (optional)${NC}"
    fi
    echo ""
fi

# Display status
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                    ${GREEN}ALL SYSTEMS READY!${NC}                     ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}🌐 Frontend:${NC}  http://localhost:3000"
echo -e "${GREEN}🔌 Backend:${NC}   http://127.0.0.1:8000"
echo -e "${GREEN}📚 API Docs:${NC}  http://127.0.0.1:8000/docs"
echo ""
echo -e "${YELLOW}💡 Tip for Codespaces:${NC}"
echo -e "   If you see a 'Privacy Error' in your browser:"
echo -e "   1. Click 'Advanced'"
echo -e "   2. Click 'Proceed to ... (unsafe)'"
echo -e "   Or use the VS Code 'Simple Browser' command."
echo ""
echo -e "${BLUE}🔥 Hot Reload Enabled:${NC}"
echo -e "   • Backend: Changes in ${YELLOW}backend/app/${NC} auto-reload"
echo -e "   • Frontend: Changes auto-reload with Vite (instant)"
echo ""
echo -e "${YELLOW}📝 Log Files:${NC}"
echo -e "   • Backend:  tail -f ${BACKEND_LOG}"
echo -e "   • Frontend: tail -f ${FRONTEND_LOG}"
[[ ! -z "$WORKER_PID" ]] && echo -e "   • Worker:   tail -f ${WORKER_LOG}"
echo ""
if [ "$START_WORKER" = true ]; then
    echo -e "${GREEN}🤖 Scraper Worker:${NC} Running in continuous mode"
else
    echo -e "${YELLOW}🤖 Scraper Worker:${NC} Not started (use ${GREEN}npm run dev:worker${NC} to enable)"
fi
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

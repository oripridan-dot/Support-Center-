#!/bin/bash

# Kill existing processes
echo "🔴 Stopping existing servers..."
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
lsof -ti:3000 | xargs -r kill -9 2>/dev/null
pkill -9 -f "uvicorn.*8000" 2>/dev/null
pkill -9 -f "vite" 2>/dev/null

sleep 2

# Start backend
echo "🚀 Starting backend on port 8000..."
cd /workspaces/Support-Center-/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

sleep 5

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend running (PID: $BACKEND_PID)"
else
    echo "⚠️  Backend still starting... (PID: $BACKEND_PID)"
fi

# Start frontend
echo "🚀 Starting frontend on port 3000..."
cd /workspaces/Support-Center-/frontend
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

sleep 5

# Check frontend
if lsof -i:3000 > /dev/null 2>&1; then
    echo "✅ Frontend running (PID: $FRONTEND_PID)"
else
    echo "❌ Frontend failed to start"
    exit 1
fi

echo ""
echo "✅ All systems running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "To stop: pkill -f 'uvicorn.*8000|vite'"

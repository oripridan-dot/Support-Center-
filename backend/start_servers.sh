#!/bin/bash
# Quick start script for Support Center application

echo "=========================================="
echo "Starting Support Center Application"
echo "=========================================="

cd /workspaces/Support-Center-/backend

echo ""
echo "🚀 Starting Backend Server on port 8000..."
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 8

echo "🚀 Starting Frontend Server on port 3000..."
cd /workspaces/Support-Center-/frontend
npm run dev &
FRONTEND_PID=$!
sleep 8

echo ""
echo "=========================================="
echo "✅ SERVERS STARTED"
echo "=========================================="
echo "Backend  (API):  http://localhost:8000"
echo "Frontend (UI):   http://localhost:3000"
echo ""
echo "Backend  PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop servers, run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "To monitor:"
echo "  tail -f /tmp/backend.log"
echo "=========================================="

wait

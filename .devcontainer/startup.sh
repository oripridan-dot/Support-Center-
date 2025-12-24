#!/bin/bash
# Codespace startup script for Halilit Support Center
# This runs automatically when the codespace starts

set -e

echo "=========================================="
echo "Halilit Support Center - Startup Script"
echo "=========================================="

cd /workspaces/Support-Center-

# Check if this is first run
if [ ! -f /tmp/.halilit_initialized ]; then
    echo "First run detected - setting up environment..."
    
    # Install Python dependencies
    if [ -f backend/requirements.txt ]; then
        echo "Installing Python dependencies..."
        pip install -q -r backend/requirements.txt
    fi
    
    # Install Node dependencies
    if [ -f frontend/package.json ]; then
        echo "Installing Node dependencies..."
        cd frontend
        npm install --silent
        cd ..
    fi
    
    touch /tmp/.halilit_initialized
    echo "✓ Environment setup complete"
fi

# Start background ingestion for Halilit brands
echo ""
echo "Starting background ingestion for Halilit brands (Brand-by-Brand)..."
echo "This will run in the background and may take 30-60 minutes."
echo "Check progress: tail -f /tmp/halilit_ingestion.log"
echo "To ingest a specific brand: ./scripts/ingest_single_brand.sh \"Brand Name\""

cd /workspaces/Support-Center-/backend

# Run ingestion in background - now using the improved brand-by-brand script
nohup python3 scripts/ingest_halilit_brands.py > /tmp/halilit_ingestion.log 2>&1 &
INGESTION_PID=$!

echo "Background ingestion started (PID: $INGESTION_PID)"
echo $INGESTION_PID > /tmp/halilit_ingestion.pid

# Start the backend server
echo ""
echo "Starting backend server..."
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
sleep 5

# Start the frontend
echo ""
echo "Starting frontend..."
cd /workspaces/Support-Center-/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "=========================================="
echo "✓ Startup Complete!"
echo "=========================================="
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Ingestion Status:"
echo "  Monitor: tail -f /tmp/halilit_ingestion.log"
echo "  PID: $INGESTION_PID"
echo ""
echo "Server PIDs:"
echo "  Backend: $BACKEND_PID"
echo "  Frontend: $FRONTEND_PID"
echo "=========================================="

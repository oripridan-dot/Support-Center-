#!/bin/bash

# ===================================================================
# Quick Start Script - Lightweight Implementation
# ===================================================================

set -e  # Exit on error

echo "🚀 Starting Halilit Support Center (Lightweight Mode)"
echo "=================================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "📝 Creating .env template..."
    cat > .env << 'EOF'
# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here

# Database
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
TASK_QUEUE_WORKERS=4

# Scraping
SCRAPING_CONCURRENCY=5
SCRAPING_DELAY_MS=1000

# Caching
CACHE_TTL_SECONDS=3600
EOF
    echo "✅ Created .env template"
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    echo ""
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p cache logs backend/data

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.lite.yml down

# Build and start services
echo "🏗️  Building containers..."
docker-compose -f docker-compose.lite.yml build

echo ""
echo "🚀 Starting services..."
docker-compose -f docker-compose.lite.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check health
echo ""
echo "🏥 Checking service health..."

# Check ChromaDB
if curl -s -f http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
    echo "✅ ChromaDB is healthy (port 8000)"
else
    echo "⚠️  ChromaDB not responding yet (this is normal, give it a moment)"
fi

# Check Backend
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy (port 8080)"
else
    echo "⚠️  Backend not responding yet (this is normal, give it a moment)"
fi

# Check Frontend
if curl -s -f http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy (port 5173)"
else
    echo "⚠️  Frontend not responding yet (this is normal, give it a moment)"
fi

echo ""
echo "=================================================="
echo "🎉 Halilit Support Center is starting!"
echo "=================================================="
echo ""
echo "📊 Service URLs:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:8080"
echo "   ChromaDB:  http://localhost:8000"
echo ""
echo "📖 API Documentation:"
echo "   Swagger UI: http://localhost:8080/docs"
echo "   ReDoc:      http://localhost:8080/redoc"
echo ""
echo "🔍 New Endpoints (Lightweight Features):"
echo "   Metrics:        http://localhost:8080/api/v2/metrics/stats"
echo "   Queue Status:   http://localhost:8080/api/v2/tasks/queue/status"
echo "   Cache Stats:    http://localhost:8080/api/v2/cache/stats"
echo "   System Status:  http://localhost:8080/api/v2/system/status"
echo ""
echo "📝 View logs with:"
echo "   docker-compose -f docker-compose.lite.yml logs -f"
echo ""
echo "🛑 Stop services with:"
echo "   docker-compose -f docker-compose.lite.yml down"
echo ""

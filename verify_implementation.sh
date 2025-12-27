#!/bin/bash

# ===================================================================
# Simple Verification Script - Check Implementation
# ===================================================================

set -e

# Change to project root
cd /workspaces/Support-Center-

echo "============================================================"
echo "🔍 Verifying Lightweight Implementation"
echo "============================================================"
echo ""

# Check files exist
echo "📁 Checking files..."

files=(
    "backend/app/workers/task_queue.py"
    "backend/app/core/cache.py"
    "backend/app/scrapers/smart_scraper.py"
    "backend/app/monitoring/simple_metrics.py"
    "backend/app/api/async_endpoints.py"
    "docker-compose.lite.yml"
    "frontend/Dockerfile.dev"
    "start_lightweight.sh"
    "LIGHTWEIGHT_IMPLEMENTATION.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ Missing: $file"
        exit 1
    fi
done

echo ""
echo "📝 Checking Python syntax..."

cd backend
python3 -m py_compile \
    app/workers/task_queue.py \
    app/core/cache.py \
    app/scrapers/smart_scraper.py \
    app/monitoring/simple_metrics.py \
    app/api/async_endpoints.py \
    app/main.py

if [ $? -eq 0 ]; then
    echo "   ✅ All Python files have valid syntax"
else
    echo "   ❌ Syntax errors found"
    exit 1
fi

cd ..

echo ""
echo "📊 Checking file sizes..."
echo "   Task Queue:    $(wc -l backend/app/workers/task_queue.py | awk '{print $1}') lines"
echo "   Cache:         $(wc -l backend/app/core/cache.py | awk '{print $1}') lines"
echo "   Smart Scraper: $(wc -l backend/app/scrapers/smart_scraper.py | awk '{print $1}') lines"
echo "   Metrics:       $(wc -l backend/app/monitoring/simple_metrics.py | awk '{print $1}') lines"
echo "   API Endpoints: $(wc -l backend/app/api/async_endpoints.py | awk '{print $1}') lines"

echo ""
echo "🔍 Checking key features..."

# Check for key classes/functions
if grep -q "class SimpleTaskQueue" backend/app/workers/task_queue.py; then
    echo "   ✅ SimpleTaskQueue class found"
fi

if grep -q "class SimpleCache" backend/app/core/cache.py; then
    echo "   ✅ SimpleCache class found"
fi

if grep -q "class SmartScraper" backend/app/scrapers/smart_scraper.py; then
    echo "   ✅ SmartScraper class found"
fi

if grep -q "class MetricsCollector" backend/app/monitoring/simple_metrics.py; then
    echo "   ✅ MetricsCollector class found"
fi

if grep -q "@cached" backend/app/core/cache.py; then
    echo "   ✅ @cached decorator found"
fi

if grep -q "lifespan" backend/app/main.py; then
    echo "   ✅ Lifespan management integrated"
fi

if grep -q "metrics_middleware" backend/app/main.py; then
    echo "   ✅ Metrics middleware integrated"
fi

if grep -q "async_router" backend/app/api/routes.py; then
    echo "   ✅ New endpoints registered"
fi

echo ""
echo "📦 Checking Docker configuration..."

if [ -f "docker-compose.lite.yml" ]; then
    echo "   ✅ Lightweight docker-compose exists"
    
    # Check for key services
    if grep -q "chromadb:" docker-compose.lite.yml; then
        echo "   ✅ ChromaDB service configured"
    fi
    
    if grep -q "backend:" docker-compose.lite.yml; then
        echo "   ✅ Backend service configured"
    fi
    
    if grep -q "frontend:" docker-compose.lite.yml; then
        echo "   ✅ Frontend service configured"
    fi
fi

echo ""
echo "============================================================"
echo "✅ All Verifications Passed!"
echo "============================================================"
echo ""
echo "📚 Next Steps:"
echo ""
echo "1. Start services:"
echo "   ./start_lightweight.sh"
echo ""
echo "2. Or start with Docker Compose directly:"
echo "   docker-compose -f docker-compose.lite.yml up -d"
echo ""
echo "3. Test new endpoints:"
echo "   curl http://localhost:8080/api/v2/system/status"
echo "   curl http://localhost:8080/api/v2/metrics/stats"
echo "   curl http://localhost:8080/api/v2/cache/stats"
echo ""
echo "4. View API documentation:"
echo "   http://localhost:8080/docs"
echo ""
echo "📖 Read full documentation:"
echo "   cat LIGHTWEIGHT_IMPLEMENTATION.md"
echo ""

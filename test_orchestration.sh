#!/bin/bash
# ===================================================================
# ORCHESTRATION QUICK TEST - Run this to verify everything works
# ===================================================================

echo "🧪 Testing Halilit Support Center Orchestration System..."
echo ""

BASE_URL="http://localhost:8080"

# Check if server is running
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "❌ Server not running on port 8080"
    echo "Start with: cd backend && uvicorn app.main:app --reload --port 8080"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Test 1: Health Check
echo "📋 Test 1: Health Check"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

# Test 2: System Status
echo "📊 Test 2: System Status"
curl -s "$BASE_URL/api/system/status" | python3 -m json.tool
echo ""

# Test 3: Queue a Task
echo "⚡ Test 3: Queue Async Task"
RESPONSE=$(curl -s -X POST "$BASE_URL/api/test/task?delay=2")
echo "$RESPONSE" | python3 -m json.tool
TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")
echo ""

# Wait a moment
echo "⏳ Waiting 3 seconds for task to complete..."
sleep 3
echo ""

# Test 4: Check Task Result
echo "📝 Test 4: Check Task Result"
curl -s "$BASE_URL/api/tasks/$TASK_ID" | python3 -m json.tool
echo ""

# Test 5: Test Caching (First call - slow)
echo "🗄️  Test 5a: Cache Test (First call - slow)"
echo "⏱️  Timing first call..."
time curl -s "$BASE_URL/api/test/cache" > /dev/null
echo ""

# Test 5: Test Caching (Second call - fast)
echo "🗄️  Test 5b: Cache Test (Second call - fast)"
echo "⏱️  Timing second call..."
time curl -s "$BASE_URL/api/test/cache" | python3 -m json.tool
echo ""

# Test 6: Task Queue Status
echo "🔧 Test 6: Task Queue Status"
curl -s "$BASE_URL/api/tasks/queue/status" | python3 -m json.tool
echo ""

# Test 7: Metrics Summary
echo "📈 Test 7: Metrics Summary"
curl -s "$BASE_URL/monitoring/metrics-summary" | python3 -m json.tool
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ ALL TESTS COMPLETE!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📚 View full API docs at: $BASE_URL/docs"
echo "🔍 View metrics at: $BASE_URL/monitoring/metrics-summary"
echo "⚙️  View system status at: $BASE_URL/api/system/status"
echo ""

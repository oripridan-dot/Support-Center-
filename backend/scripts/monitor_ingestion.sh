#!/bin/bash
# Monitor continuous ingestion progress
# Usage: ./scripts/monitor_ingestion.sh

echo "🔄 Continuous Ingestion Monitor"
echo "================================"
echo ""

if [ -f "/tmp/continuous_ingestion_output.log" ]; then
    echo "📊 Latest ingestion events:"
    tail -20 /tmp/continuous_ingestion_output.log | grep -E "Starting|✅|❌|CYCLE|Duration"
    echo ""
fi

if [ -f "/tmp/ingestion_status.json" ]; then
    echo "📈 Ingestion status:"
    cat /tmp/ingestion_status.json | python3 -m json.tool 2>/dev/null | head -30
    echo ""
fi

echo "Process status:"
pgrep -f continuous_ingestion >/dev/null && echo "✅ Service running (PID: $(pgrep -f continuous_ingestion))" || echo "❌ Service stopped"

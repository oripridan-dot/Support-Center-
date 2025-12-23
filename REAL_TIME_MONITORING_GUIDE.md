# Real-Time Ingestion Monitoring Guide

## Overview

The comprehensive brand documentation ingestion now has **full real-time monitoring** integrated into the UI and API. Track ingestion progress live as it discovers URLs, processes documents, and updates the database.

---

## Components

### 1. **Backend: Ingestion Tracker Service**
- **File:** `backend/app/services/ingestion_tracker.py`
- **Purpose:** Thread-safe tracking of ingestion progress
- **Features:**
  - Writes status to JSON file (`/tmp/ingestion_status.json`)
  - Tracks per-brand progress with detailed status
  - Records errors without stopping ingestion
  - Updates in real-time as documents are processed

### 2. **API Endpoints**
- **Status Endpoint:** `GET /api/ingestion/status`
  - Returns current ingestion status as JSON
  - HTTP polling or manual queries

- **WebSocket Endpoint:** `WS /api/ingestion/ws/status`
  - Real-time updates via WebSocket
  - Automatic reconnection with fallback to polling
  - ~500ms update frequency

- **Stats Endpoint:** `GET /api/ingestion/stats`
  - Quick statistics about current ingestion
  - Document counts, error tracking, progress

### 3. **Frontend: IngestionMonitor Component**
- **File:** `frontend/components/IngestionMonitor.tsx`
- **Features:**
  - WebSocket-based real-time updates (fallback to polling)
  - Auto-show/hide based on ingestion state
  - Progress bar with percentage
  - Per-brand progress tracking
  - Error display
  - Last updated timestamp

---

## Real-Time Data Flow

```
Ingestion Script (ingest_comprehensive_brands.py)
        ↓
Calls: tracker.update_brand_start(), tracker.update_urls_discovered(), etc.
        ↓
IngestionTracker writes to: /tmp/ingestion_status.json
        ↓
FastAPI reads and serves via: /api/ingestion/status (polling) OR /ws/status (WebSocket)
        ↓
Frontend IngestionMonitor displays real-time updates
```

---

## Monitoring Methods

### Method 1: Web UI (Recommended)
The ingestion monitor automatically displays when ingestion starts. It shows:
- Current brand being processed
- Current step (discovering/processing)
- Overall progress percentage
- Per-brand document counts
- URLs discovered and processed
- Real-time errors

**Access:** http://localhost:3001 (appears in bottom-right corner when active)

### Method 2: API Polling (Manual)
```bash
# Check status every 2 seconds
while true; do
  curl -s http://localhost:8000/api/ingestion/status | jq '{
    current_brand,
    urls_discovered,
    progress_percent,
    total_documents,
    documents_by_brand
  }'
  sleep 2
done
```

### Method 3: Log Files
```bash
# Watch ingestion logs in real-time
tail -f /workspaces/Support-Center-/backend/ingest_comprehensive.log
```

### Method 4: Direct Status File
```bash
# Check raw status JSON
cat /tmp/ingestion_status.json | jq '.'

# Watch for changes every second
watch -n1 'cat /tmp/ingestion_status.json | jq ".current_step, .progress_percent"'
```

---

## Status JSON Structure

```json
{
  "is_running": true,
  "current_brand": "Rode",
  "current_step": "Processing Rode: 45/250 docs",
  "total_documents": 45,
  "documents_by_brand": {
    "Rode": 45
  },
  "urls_discovered": 235,
  "urls_processed": 45,
  "progress_percent": 19.1,
  "last_updated": "2025-12-23T22:30:45.123456",
  "errors": [
    {
      "timestamp": "2025-12-23T22:30:40.234567",
      "message": "Timeout on https://..."
    }
  ],
  "start_time": "2025-12-23T22:24:26.115009",
  "estimated_completion": "",
  "brand_progress": {
    "Rode": {
      "brand_id": 5,
      "status": "processing",
      "urls_discovered": 235,
      "documents_ingested": 45,
      "start_time": "2025-12-23T22:24:27.226423"
    },
    "Boss": {
      "brand_id": 2,
      "status": "pending",
      "urls_discovered": 0,
      "documents_ingested": 0,
      "start_time": ""
    }
  }
}
```

### Key Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `is_running` | bool | Whether ingestion is active |
| `current_brand` | string | Brand currently being processed |
| `current_step` | string | Detailed status of current operation |
| `total_documents` | int | All documents ingested so far |
| `documents_by_brand` | object | Per-brand document count |
| `urls_discovered` | int | Total URLs found across all brands |
| `urls_processed` | int | URLs ingested so far |
| `progress_percent` | float | Overall progress (0-100) |
| `brand_progress` | object | Detailed progress per brand |
| `errors` | array | Errors encountered (non-fatal) |

---

## Expected Timeline

```
Start → Rode (30-40 min) → Boss (20-30 min) → Roland (40-50 min) 
        → Mackie (30-40 min) → PreSonus (30-40 min) → Complete
        
Total: ~2-2.5 hours
Target: 1,280+ new documents
```

### Phase Breakdown

**Rode Phase (Currently Active)**
- URLs to discover: 250-300
- Target documents: 250+
- Status categories: Support (80 URLs) + Products (120 URLs) + Specs (100 URLs)
- ETA: 30-40 minutes

---

## Starting Ingestion

### Manual Start
```bash
cd /workspaces/Support-Center-/backend
export PYTHONPATH=.
python scripts/ingest_comprehensive_brands.py > ingest_comprehensive.log 2>&1 &
```

### With Real-Time Monitoring
```bash
# Terminal 1: Start ingestion
cd /workspaces/Support-Center-/backend && PYTHONPATH=. python scripts/ingest_comprehensive_brands.py

# Terminal 2: Watch API (if no UI available)
watch -n 2 'curl -s http://localhost:8000/api/ingestion/status | jq -c "{brand: .current_brand, progress: .progress_percent, urls: .urls_discovered}"'

# Terminal 3: Check logs
tail -f /workspaces/Support-Center-/backend/ingest_comprehensive.log
```

---

## Stopping Ingestion

```bash
# Find the process
ps aux | grep "ingest_comprehensive" | grep -v grep

# Kill it gracefully (will complete current document)
kill <PID>

# Force kill if needed
kill -9 <PID>
```

---

## Troubleshooting

### No Real-Time Updates
1. **Check if status file exists:**
   ```bash
   ls -la /tmp/ingestion_status.json
   ```

2. **Check if API is running:**
   ```bash
   curl http://localhost:8000/api/ingestion/status
   ```

3. **Check if ingestion script is running:**
   ```bash
   ps aux | grep ingest_comprehensive
   ```

### WebSocket Not Connecting
- Falls back to polling automatically
- Check browser console for errors
- Verify API server is running on port 8000

### Slow Updates
- WebSocket defaults to 500ms polling
- Adjust in `IngestionMonitor.tsx` if needed
- API polling fallback is every 1 second

---

## Performance Notes

- **Status writes:** Only on updates (not every iteration)
- **Thread-safe:** Uses `threading.Lock()` for concurrent access
- **Memory:** Minimal (~1MB for status file)
- **CPU:** Negligible overhead from tracking

---

## Integration Points

### For Ingestion Scripts
Add to your script header:
```python
from app.services.ingestion_tracker import tracker

# Start
tracker.start()

# During processing
tracker.update_brand_start(brand_name, brand_id)
tracker.update_urls_discovered(brand_name, url_count)
tracker.update_document_count(brand_name, doc_count)
tracker.update_brand_complete(brand_name, final_count)

# On error
tracker.add_error(error_message)

# On completion
tracker.complete()
```

### For Custom Monitoring
```python
from app.services.ingestion_tracker import tracker
import json

status = tracker.status
print(f"Current: {status['current_brand']}")
print(f"Progress: {status['progress_percent']:.1f}%")
print(f"Docs: {status['total_documents']}")
```

---

## Verification Checklist

After ingestion completes:

- [ ] ✅ COMPREHENSIVE INGESTION COMPLETE message in logs
- [ ] Status JSON shows `is_running: false`, `progress_percent: 100.0`
- [ ] All 5 brands show in `documents_by_brand`
- [ ] Total documents ≥ 1,280
- [ ] No unrecovered errors in error list
- [ ] UI monitor shows completion
- [ ] Database query confirms new documents:
  ```bash
  cd backend && PYTHONPATH=. python -c "
  from app.core.database import Session, engine
  from app.models.sql_models import Document
  from sqlmodel import select
  with Session(engine) as session:
      count = len(session.exec(select(Document)).all())
      print(f'Total documents: {count}')
  " | grep Total
  ```

---

## Next Steps

1. **Monitor in Real-Time**
   - Open http://localhost:3001 to see the UI monitor
   - Or use API endpoints above

2. **After Completion**
   - Verify document count
   - Test API queries with new documents
   - Check search accuracy

3. **Phase 2 Continuation**
   - Same tracking will work for future ingestions
   - Reset tracker: `POST /api/ingestion/reset`
   - Run additional brands with same pattern

---

**Last Updated:** December 23, 2025  
**Status:** 🟢 Live - Real-time monitoring active during ingestion

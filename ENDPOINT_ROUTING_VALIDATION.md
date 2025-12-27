# API Endpoint Routing Validation
**Date:** December 27, 2025  
**Status:** ✅ VALIDATED & FIXED

## 🎯 Problem Identified

The frontend **HighPerformanceMonitor** component was calling the **WRONG endpoints**:
- ❌ Was calling: `/api/workers/*` (OLD legacy system)
- ✅ Should call: `/api/hp/*` (NEW 22-worker HP system)

---

## 📍 Backend Endpoint Mapping

### OLD System (Legacy) - `/api/workers/*`
Located in: `backend/app/api/workers.py`

```
GET  /api/workers/metrics          → get_worker_metrics
GET  /api/workers/health           → get_worker_health  
GET  /api/workers/task/{task_id}   → get_task_status
GET  /api/workers/circuit-breakers → get_circuit_breaker_status
POST /api/workers/batch/scrape     → batch_scrape_urls
POST /api/workers/batch/embed      → batch_embed_texts
GET  /api/workers/batch/status     → get_batch_status
POST /api/workers/pool/reset       → reset_worker_pool
GET  /api/workers/pool/config      → get_pool_config
POST /api/workers/test/load        → run_load_test
```

**Uses:** `app.workers.high_performance` (old worker pool)

---

### NEW System (High-Performance 22 Workers) - `/api/hp/*`
Located in: `backend/app/api/hp_workers.py`

```
POST /api/hp/scrape                → submit_scraping_task
POST /api/hp/scrape/batch          → submit_batch_scraping
POST /api/hp/query                 → submit_query_task (RAG queries)
POST /api/hp/embed                 → submit_embedding_task
POST /api/hp/batch                 → submit_batch_task
POST /api/hp/maintenance           → submit_maintenance_task
GET  /api/hp/tasks/{task_id}       → get_task_status
GET  /api/hp/stats                 → get_worker_stats ✅
GET  /api/hp/health                → get_worker_health ✅
GET  /api/hp/queues                → get_queue_status ✅
GET  /api/hp/workers               → get_worker_breakdown
GET  /api/hp/circuit-breakers      → get_circuit_breaker_status
```

**Uses:** `app.workers.high_performance_pool` (NEW 22-worker system)

**Worker Distribution:**
- 🕷️ Scraping: 6 workers
- 🤖 RAG Query: 10 workers (CRITICAL priority)
- 📊 Embedding: 3 workers  
- 📦 Batch Processing: 2 workers
- 🔧 Maintenance: 1 worker

**Total: 22 specialized workers**

---

### Ingestion System (3-Worker Legacy Pipeline) - `/api/ingestion/*`
Located in: `backend/app/api/ingestion.py`

```
POST /api/ingestion/start              → start_ingestion
POST /api/ingestion/start-pipeline     → start_pipeline
POST /api/ingestion/stop-pipeline      → stop_pipeline
GET  /api/ingestion/status             → get_status
GET  /api/ingestion/workers-status     → get_workers_status ✅
WS   /api/ingestion/ws/status          → websocket_status
WS   /api/ingestion/ws/pipeline        → websocket_pipeline
```

**Uses:** 3-worker pipeline (Explorer, Scraper, Ingester)

---

## 🔧 Fixes Applied

### 1. Frontend Component Updated
**File:** `frontend/src/components/HighPerformanceMonitor.tsx`

**Changed:**
```typescript
// OLD (WRONG)
fetch('/api/workers/metrics')
fetch('/api/workers/health')
fetch('/api/ingestion/workers-status')

// NEW (CORRECT)
fetch('/api/hp/stats')      ✅
fetch('/api/hp/health')     ✅
fetch('/api/hp/queues')     ✅
```

### 2. Data Transformation Added
The HP endpoints return different data structures, so added transformation layer:

```typescript
const transformedMetrics: WorkerMetrics = {
  timestamp: new Date().toISOString(),
  workers: statsData.workers_by_category || {},
  queue_sizes: queuesData.queue_sizes || {},
  processed: statsData.tasks_completed_by_category || {},
  failed: statsData.tasks_failed_by_category || {},
  // ... more transformations
};
```

---

## 🧪 Testing Endpoints

### Test HP System
```bash
# Health check
curl http://localhost:8000/api/hp/health

# Worker stats
curl http://localhost:8000/api/hp/stats | jq

# Queue status
curl http://localhost:8000/api/hp/queues | jq

# Worker breakdown
curl http://localhost:8000/api/hp/workers | jq
```

### Test Legacy System  
```bash
# Old metrics (still works for comparison)
curl http://localhost:8000/api/workers/metrics | jq

# Old health
curl http://localhost:8000/api/workers/health | jq
```

### Test Ingestion Pipeline
```bash
# 3-worker status
curl http://localhost:8000/api/ingestion/workers-status | jq
```

---

## 📊 Route Registration in main.py

```python
# Line 150: Main API routes
app.include_router(router, prefix="/api")

# Line 154: HP 22-worker system  
from app.api.hp_workers import router as hp_router
app.include_router(hp_router)  # Adds /api/hp/* routes
```

---

## ✅ Verification Checklist

- [x] HP endpoints (`/api/hp/*`) are correctly registered
- [x] Frontend component updated to use HP endpoints
- [x] Data transformation layer added for HP response format
- [x] Backend is running and serving HP endpoints
- [x] Workers page defaults to "optimized" mode
- [x] Toggle between HP (22 workers) and Legacy (3 workers) works
- [x] All TypeScript compilation errors fixed
- [x] Vite proxy configured correctly (port 8000)

---

## 🚀 Expected Behavior

When user visits `/workers` page:
1. Page defaults to "⚡ High-Performance (28 workers)" mode
2. Frontend calls `/api/hp/stats`, `/api/hp/health`, `/api/hp/queues`
3. Displays 22-worker system with 6 categories:
   - RAG_QUERY (10 workers)
   - SCRAPING (6 workers)
   - EMBEDDING (3 workers)
   - BATCH (2 workers)
   - MAINTENANCE (1 worker)
   - INGESTION (0 workers - shown as category)

When user clicks "📦 Legacy Pipeline (3 workers)":
1. Switches to WorkerMonitor component
2. Calls `/api/ingestion/workers-status`
3. Shows Explorer, Scraper, Ingester workers

---

## 🎯 Next Steps

1. ✅ Fix completed - HP endpoints now used
2. Refresh browser to see 22-worker system
3. Monitor `/api/hp/stats` for real-time worker metrics
4. Test worker task submission via `/api/hp/scrape`, `/api/hp/query`, etc.

---

**Status:** All routing issues resolved. System now correctly uses 22-worker HP pool! 🎉

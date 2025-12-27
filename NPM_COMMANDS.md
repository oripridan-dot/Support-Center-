# 🚀 22-Worker System: npm Commands

## Development Commands

### Start Development Environment
```bash
npm run dev
```
**What it does:**
- ✅ Starts FastAPI backend on http://127.0.0.1:8000
- ✅ Starts React frontend on http://localhost:3000
- ✅ Initializes 22-worker high-performance system
- ✅ Enables hot reload for both frontend and backend
- ✅ Shows worker system status on startup

**Output:**
```
╔══════════════════════════════════════════════════════════════╗
║        🎵  Halilit Support Center - Dev Mode  🎵         ║
╚══════════════════════════════════════════════════════════════╝

🔍 Checking ports...
✅ Ports are ready

🚀 Starting Backend (FastAPI)...
✅ Backend running on http://127.0.0.1:8000

🚀 Starting Frontend (Vite + React)...
✅ Frontend running on http://localhost:3000

⚡ 22-Worker System: ✅ OPERATIONAL
   • Scraping: 6 workers  • RAG Query: 10 workers
   • Embedding: 3 workers • Batch: 2 workers
   • Maintenance: 1 worker
   Monitor: http://127.0.0.1:8000/api/hp/workers
```

---

## Worker Testing & Monitoring

### Run Full Test Suite
```bash
npm run test:workers
```
**What it does:**
- Runs all 10 comprehensive tests
- Tests all 5 worker categories
- Verifies priority handling
- Checks circuit breakers
- Measures performance

**Expected output:**
```
✅ 10/10 TESTS PASSED
✅ System Health
✅ Worker Configuration
✅ Scraping Workers (6)
✅ RAG Query Workers (10)
✅ Embedding Workers (3)
✅ Batch Workers (2)
✅ Maintenance Worker (1)
✅ Priority Handling
✅ Circuit Breakers
✅ Comprehensive Stats
```

---

### Check Worker Health
```bash
npm run workers:health
```
**Output:**
```json
{
  "healthy": true,
  "running": true,
  "workers": {
    "healthy": 22,
    "total": 22,
    "health_percentage": 100.0
  },
  "circuit_breakers": {
    "openai": "closed",
    "chromadb": "closed",
    "playwright": "closed"
  }
}
```

---

### View Worker Statistics
```bash
npm run workers:stats
```
**Output:**
```json
{
  "running": true,
  "workers": {
    "total": 22,
    "by_category": {
      "scraping": 6,
      "rag_query": 10,
      "embedding": 3,
      "batch_processing": 2,
      "maintenance": 1
    }
  },
  "queues": {
    "scraping": 0,
    "rag_query": 0,
    "embedding": 0,
    "batch_processing": 0,
    "maintenance": 0
  },
  "metrics": {
    "submitted": {...},
    "completed": {...},
    "failed": {...}
  }
}
```

---

### Check Worker Status by Category
```bash
npm run workers:status
```
**Output:**
```json
{
  "total_workers": 22,
  "categories": {
    "scraping": {
      "workers": 6,
      "queue_size": 0,
      "tasks_completed": 18,
      "avg_duration": 2.00
    },
    "rag_query": {
      "workers": 10,
      "queue_size": 0,
      "tasks_completed": 5,
      "avg_duration": 1.00
    },
    ...
  }
}
```

---

## Available npm Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start full dev environment with 22-worker system |
| `npm run dev:worker` | Start with optional scraper worker |
| `npm run test:workers` | Run comprehensive worker test suite |
| `npm run workers:health` | Check 22-worker system health |
| `npm run workers:stats` | View detailed statistics |
| `npm run workers:status` | View worker breakdown by category |
| `npm run backend` | Start backend only |
| `npm run frontend` | Start frontend only |
| `npm run install-all` | Install all dependencies |

---

## Quick Workflows

### 1. Normal Development
```bash
npm run dev
# Opens:
# - Frontend: http://localhost:3000
# - Backend: http://127.0.0.1:8000
# - API Docs: http://127.0.0.1:8000/docs
# - Worker Monitor: http://127.0.0.1:8000/api/hp/workers
```

### 2. Testing Workers
```bash
npm run dev        # Terminal 1 - Start services
npm run test:workers    # Terminal 2 - Run tests
```

### 3. Monitoring During Development
```bash
# Terminal 1: Dev environment
npm run dev

# Terminal 2: Watch worker health
watch -n 2 'npm run workers:health'

# Terminal 3: Watch statistics
watch -n 5 'npm run workers:stats'
```

### 4. Backend Logs
```bash
# While npm run dev is running:
tail -f /tmp/backend_dev.log
```

**Look for:**
```
✅ hp_22_worker_pool_started      
   scraping=6 rag_query=10 embedding=3 batch=2 maintenance=1
   total_workers=22
```

---

## API Endpoints (Available After npm run dev)

### Monitoring Endpoints
```bash
# Health check
curl http://127.0.0.1:8000/api/hp/health

# Statistics
curl http://127.0.0.1:8000/api/hp/stats

# Worker breakdown
curl http://127.0.0.1:8000/api/hp/workers

# Queue status
curl http://127.0.0.1:8000/api/hp/queues

# Circuit breakers
curl http://127.0.0.1:8000/api/hp/circuit-breakers
```

### Task Submission
```bash
# Submit scraping task
curl -X POST http://127.0.0.1:8000/api/hp/scrape \
  -H "Content-Type: application/json" \
  -d '{"url":"https://test.com","brand":"halilit","priority":"NORMAL"}'

# Submit query (CRITICAL priority)
curl -X POST http://127.0.0.1:8000/api/hp/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How to use Halilit djembe?","priority":"CRITICAL"}'

# Check task status
curl http://127.0.0.1:8000/api/hp/tasks/{task_id}
```

---

## Troubleshooting

### Issue: Workers not showing as healthy
```bash
# Check backend logs
tail -30 /tmp/backend_dev.log

# Look for:
# ✅ hp_22_worker_pool_started

# If not found, restart:
pkill -f uvicorn
npm run dev
```

### Issue: Ports already in use
```bash
# Dev script automatically cleans up ports
# But if needed, manually:
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Then restart:
npm run dev
```

### Issue: Test failures
```bash
# Make sure server is running:
npm run dev  # Terminal 1

# Run tests:
npm run test:workers  # Terminal 2

# Check specific endpoint:
npm run workers:health
```

---

## Integration Status

✅ **Hooked into `npm run dev`**
- 22-worker system starts automatically
- Status shown on startup
- Health checks integrated
- Monitoring commands available

✅ **Test Commands Added**
- `npm run test:workers` - Full test suite
- `npm run workers:health` - Quick health check
- `npm run workers:stats` - Detailed statistics
- `npm run workers:status` - Worker breakdown

✅ **Development Experience**
- Hot reload for backend changes
- Hot reload for frontend changes
- Real-time worker monitoring
- Comprehensive logging

---

## Next Steps

1. **Start developing:**
   ```bash
   npm run dev
   ```

2. **Monitor workers:**
   ```bash
   npm run workers:status
   ```

3. **Run tests:**
   ```bash
   npm run test:workers
   ```

4. **Check health:**
   ```bash
   npm run workers:health
   ```

**The 22-worker system is now fully integrated into your development workflow!** 🚀

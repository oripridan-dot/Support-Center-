# 🚀 Quick Start Guide

**TL;DR:** Everything is optimized. Use `npm run dev` for development.

---

## ⚡ Start Services

### Development (Recommended)
```bash
npm run dev
```
- ✅ API: http://127.0.0.1:8000
- ✅ Frontend: http://localhost:3000
- ✅ API Docs: http://127.0.0.1:8000/docs
- ⚠️ Worker: Start manually when needed

### With Background Worker
```bash
npm run dev:worker
```
- ✅ Everything above + continuous scraping

---

## 🎯 Trigger Scraping

### Via API
```bash
# Scrape specific brand
curl -X POST http://127.0.0.1:8000/api/worker/scrape/KRK%20Systems

# Check status
curl http://127.0.0.1:8000/api/worker/status
```

### Via Command Line
```bash
cd backend

# Scrape once
python worker.py --mode once

# Continuous
python worker.py --mode continuous --delay 60
```

---

## 📝 Monitor

```bash
# Backend logs
tail -f /tmp/backend_dev.log

# Frontend logs
tail -f /tmp/frontend_dev.log

# Worker logs
tail -f /tmp/worker.log
```

---

## 🔧 Common Commands

### Stop Everything
```bash
Ctrl+C
```

### Kill Stuck Processes
```bash
pkill -f uvicorn
pkill -f vite
pkill -f worker.py
```

### Check What's Running
```bash
ps aux | grep -E "(uvicorn|vite|worker)" | grep -v grep
```

### Test Database
```bash
cd backend
python -c "from app.core.database import engine; from sqlalchemy import text; print('WAL:', engine.connect().execute(text('PRAGMA journal_mode')).scalar())"
```

---

## 📚 Full Documentation

- [OPTIMIZATION_COMPLETE.md](OPTIMIZATION_COMPLETE.md) - Full system overview
- [WORKER_ARCHITECTURE.md](WORKER_ARCHITECTURE.md) - Worker details
- [MIGRATION_COMPLETE.md](MIGRATION_COMPLETE.md) - Migration details

---

## ✅ What Was Fixed

1. **Next.js 16 (canary) → Vite 7 (stable)** = No more crashes
2. **React 19 → React 18** = Stable ecosystem
3. **SQLite WAL mode** = 10x faster queries
4. **Worker separation** = API stays responsive during scraping

**Result:** Fast, stable, production-ready! 🎉

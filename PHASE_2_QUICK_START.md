# 🚀 Phase 2 Execution: Quick Start Guide

## Current Status

### ✅ Phase 1 Complete
- **Allen & Heath:** 250 documents
- **RCF:** 1,236 documents
- **Total:** 1,486 documents stored in database
- **Vector Index:** Indexed in ChromaDB
- **Backend Server:** Running on port 8000
- **Frontend Server:** Running on port 3001

---

## 📋 Phase 2 Target Brands

| Brand | Target Docs | Status | Support Method |
|-------|------------|--------|-----------------|
| **Rode** | 200+ | ⏳ In Progress | Browser automation + discovery |
| **Boss** | 150+ | 🔜 Ready | Browser automation + discovery |
| **Roland** | 250+ | 🔜 Ready | Browser automation + discovery |
| **Mackie** | 180+ | 🔜 Ready | Browser automation + discovery |
| **PreSonus** | 200+ | 🔜 Ready | Browser automation + discovery |

**Phase 2 Total Target:** 980+ documents  
**Combined Target (Phase 1 + 2):** 2,500+ documents

---

## 🎯 Execution Strategy

### Sequential Approach (Recommended)
1. **Rode** - 200 documents (~5 minutes)
2. **Boss** - 150 documents (~4 minutes)  
3. **Roland** - 250 documents (~6 minutes)
4. **Mackie** - 180 documents (~5 minutes)
5. **PreSonus** - 200 documents (~5 minutes)

**Total Duration:** ~25 minutes

### Key Features
✅ Automatic URL discovery  
✅ Browser-based navigation (handles JavaScript)  
✅ Duplicate prevention (content hash checking)  
✅ Graceful error recovery  
✅ Batch processing optimization  
✅ Real-time progress logging  

---

## 🔧 How to Run Phase 2

### Option 1: Automatic (Recommended)
```bash
cd /workspaces/Support-Center-/backend
export PYTHONPATH=.
python scripts/ingest_phase2_brands.py
```

**Output:** `ingest_phase2.log`  
**Time:** ~25 minutes for all 5 brands

### Option 2: Monitor Progress
```bash
# Terminal 1: Run ingestion
cd /workspaces/Support-Center-/backend && PYTHONPATH=. python scripts/ingest_phase2_brands.py

# Terminal 2: Monitor logs (in another terminal)
tail -f /workspaces/Support-Center-/backend/ingest_phase2.log
```

### Option 3: Check Database Progress
```bash
# Check current document counts
cd /workspaces/Support-Center-/backend && python3 -c "
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

with Session(engine) as session:
    brands = session.exec(select(Brand)).all()
    for brand in brands:
        docs = len(session.exec(select(Document).where(Document.brand_id == brand.id)).all())
        if docs > 0:
            print(f'{brand.name}: {docs} documents')
" 2>&1 | grep -E "Rode|Boss|Roland|Mackie|PreSonus|Total"
```

---

## 📊 Expected Results After Phase 2

| Metric | Value |
|--------|-------|
| Total Documents | 2,400+ |
| Allen & Heath | 250 (100%) |
| RCF | 1,236 (100%) |
| Rode | 200+ |
| Boss | 150+ |
| Roland | 250+ |
| Mackie | 180+ |
| PreSonus | 200+ |
| Database Size | ~250 MB |
| ChromaDB Vectors | 2,400+ |

---

## 🔍 Testing Phase 2 Results

### Test API Query
```bash
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Rode microphone specifications?",
    "brand": "rode",
    "top_k": 3
  }'
```

### Test Frontend
```
Open browser: http://localhost:3001
Search for: "Rode microphone" or "Boss effects" or "Roland keyboard"
```

### Check Database
```bash
PYTHONPATH=. python -c "
from app.core.database import Session, engine
from app.models.sql_models import Document
from sqlmodel import select

with Session(engine) as session:
    total = len(session.exec(select(Document)).all())
    print(f'Total documents in database: {total}')
" 2>&1 | grep Total
```

---

## 📈 Monitoring Ingestion

### Real-Time Progress
The script logs:
- ✅ Discovered URLs
- ✅ Ingested documents count
- ✅ Processing time per brand
- ✅ Error summary
- ✅ Final statistics

### Log File Location
```
/workspaces/Support-Center-/backend/ingest_phase2.log
```

### Monitor Command
```bash
# Watch log updates in real-time
tail -f /workspaces/Support-Center-/backend/ingest_phase2.log
```

---

## ✅ Phase 2 Completion Checklist

After running Phase 2 ingestion:

- [ ] Rode documents ingested (200+ expected)
- [ ] Boss documents ingested (150+ expected)
- [ ] Roland documents ingested (250+ expected)
- [ ] Mackie documents ingested (180+ expected)
- [ ] PreSonus documents ingested (200+ expected)
- [ ] Total documents ~2,400+
- [ ] API responding with new brand queries
- [ ] Frontend searchable with new content
- [ ] No errors in logs (except warnings are OK)
- [ ] Ingestion completed successfully

---

## 🐛 Troubleshooting

### If Script Hangs
```bash
# Kill running process
pkill -f ingest_phase2_brands.py

# Check logs for errors
tail -100 /workspaces/Support-Center-/backend/ingest_phase2.log
```

### If Brand Returns 0 Documents
1. Check the brand's support website structure
2. Verify support URLs are correct
3. Check network connectivity
4. Review logs for specific errors

### If Database Issues
```bash
# Reset database and restart
cd /workspaces/Support-Center-/backend
rm -f database.db  # WARNING: This deletes everything!
python -c "from app.core.database import create_db_and_tables; create_db_and_tables()"
```

---

## 📞 Summary

**Status:** Ready to execute Phase 2  
**Estimated Duration:** ~25 minutes  
**Target:** 980+ new documents  
**Risk Level:** Low (proven method from Phase 1)  

Run the script and monitor the logs. All 5 brands will be ingested sequentially.

---

**Next Action:** Execute Phase 2 ingestion  
**Expected Completion:** 25 minutes  
**Verification:** Check database document count afterwards

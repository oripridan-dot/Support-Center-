# 🚀 Comprehensive Brand Documentation Ingestion - Quick Start

## One-Command Execution

```bash
cd /workspaces/Support-Center-/backend && \
PYTHONPATH=. python scripts/ingest_comprehensive_brands.py 2>&1 | tee -a ingest_comprehensive.log &
```

## What This Does

✅ **Support Centers** - Ingests FAQs, knowledge bases, help articles  
✅ **Product Documentation** - Captures product pages, specs, features  
✅ **Official Specifications** - Extracts manuals, guides, technical specs  
✅ **All 5 Brands** - Rode, Boss, Roland, Mackie, PreSonus

## Expected Results

| Brand | Support | Products | Specs | Total |
|-------|---------|----------|-------|-------|
| Rode | 40 | 60 | 30 | **250+** |
| Boss | 35 | 50 | 25 | **200+** |
| Roland | 50 | 100 | 50 | **300+** |
| Mackie | 40 | 80 | 30 | **250+** |
| PreSonus | 45 | 90 | 45 | **280+** |
| **TOTAL** | **210** | **380** | **180** | **1,280+** |

**Combined with Phase 1:** 2,766+ total documents

## Monitoring Progress

### Real-time Log
```bash
tail -f /workspaces/Support-Center-/backend/ingest_comprehensive.log
```

### Check Current Document Count
```bash
cd /workspaces/Support-Center-/backend && python3 -c "
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

with Session(engine) as session:
    total = len(session.exec(select(Document)).all())
    print(f'Total documents: {total}')
    
    brands = session.exec(select(Brand)).all()
    for brand in brands:
        count = len(session.exec(
            select(Document).where(Document.brand_id == brand.id)
        ).all())
        if count > 0:
            print(f'  {brand.name:15s}: {count:4d}')
" 2>&1 | grep -v INFO
```

### Check Process Status
```bash
ps aux | grep ingest_comprehensive | grep -v grep
```

## Timing Estimate

- **Rode**: ~30-40 min (250 docs)
- **Boss**: ~20-30 min (200 docs)
- **Roland**: ~40-50 min (300 docs)
- **Mackie**: ~30-40 min (250 docs)
- **PreSonus**: ~30-40 min (280 docs)
- **Total**: ~2-2.5 hours (1,280+ docs)

## After Completion (Verification)

```bash
# Get final summary
tail -50 /workspaces/Support-Center-/backend/ingest_comprehensive.log | tail -20

# Check final document count
echo "Final Database Status:"
PYTHONPATH=. python3 -c "
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

with Session(engine) as session:
    total = len(session.exec(select(Document)).all())
    print(f'✅ Total documents: {total}')
" 2>&1 | grep Total
```

## Testing the Results

```bash
# Query for Roland documentation
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I set up a Roland keyboard?",
    "brand_id": 1
  }' 2>/dev/null | jq '.answer[:300]'

# Query for RODE microphone setup
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "RODE microphone connection setup",
    "brand_id": 5
  }' 2>/dev/null | jq '.answer[:300]'
```

## Key Features

✅ **Comprehensive Coverage**
- Support centers + product docs + specifications
- Multiple URL sources per category
- Deep crawling (150+ URLs per category)

✅ **Smart Deduplication**
- Content hashing to prevent duplicates
- URL tracking to avoid re-ingestion
- Intelligent cross-source deduplication

✅ **Quality Control**
- Minimum content length enforcement
- Main content extraction
- Metadata preservation

✅ **Error Handling**
- Timeout recovery
- Connection retries
- Graceful error reporting

## Documentation Files

Created for reference:
- **COMPREHENSIVE_DOCUMENTATION_STRATEGY.md** - Full strategy & sources
- **DOCUMENTATION_ARCHITECTURE.md** - How it works & examples
- **ingest_comprehensive_brands.py** - Execution script

---

**Status:** Ready to execute  
**Expected Start Time:** Now  
**Expected End Time:** ~2-2.5 hours  
**Final Outcome:** 2,766+ documents across 7 brands with comprehensive support, product, and specification coverage

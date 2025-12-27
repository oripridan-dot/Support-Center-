# Worker Pipeline Documentation

## Architecture Overview

The ingestion system uses a **3-worker pipeline** for reliable, scalable documentation collection:

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   EXPLORER   │ ───► │   SCRAPER    │ ───► │   INGESTER   │
│              │      │              │      │              │
│ • Discovers  │      │ • Executes   │      │ • Vectorizes │
│ • Analyzes   │      │ • Downloads  │      │ • Indexes    │
│ • Plans      │      │ • Extracts   │      │ • Verifies   │
└──────────────┘      └──────────────┘      └──────────────┘
       │                                             │
       │                                             │
       └─────────────── Verification ───────────────┘
```

## Workers

### 1. Explorer (`app/workers/explorer.py`)

**Role**: Intelligence layer - discovers what needs to be scraped

**Responsibilities**:
- Crawls brand websites to find documentation
- Identifies navigation patterns and content structure
- Generates scraping instructions (`ScrapingStrategy`)
- Verifies completeness after ingestion

**Output**: `ScrapingStrategy` JSON with:
- List of documentation URLs
- Content selectors (CSS)
- Rate limits
- Navigation patterns

**Example Usage**:
```python
from app.workers.explorer import ExplorerWorker

explorer = ExplorerWorker()
await explorer.initialize()
strategy = await explorer.explore_brand(brand_id=4)
await explorer.shutdown()
```

### 2. Scraper (`app/workers/scraper.py`)

**Role**: Execution layer - collects documentation

**Responsibilities**:
- Follows Explorer's instructions
- Downloads PDFs and HTML pages
- Extracts text content
- Saves raw files to disk
- Passes documents to Ingester

**Input**: `ScrapingStrategy` from Explorer
**Output**: List of `ScrapedDocument` objects

**Example Usage**:
```python
from app.workers.scraper import ScraperWorker

scraper = ScraperWorker()
await scraper.initialize()
docs = await scraper.execute_strategy(strategy)
scraper.save_to_disk(docs, strategy)
await scraper.shutdown()
```

### 3. Ingester (`app/workers/ingester.py`)

**Role**: Indexing layer - makes documents searchable

**Responsibilities**:
- Chunks documents into optimal sizes
- Generates embeddings
- Stores in ChromaDB vector database
- Updates SQLite with document records
- Calls Explorer to verify completeness

**Input**: List of `ScrapedDocument` from Scraper
**Output**: Ingestion report with counts and verification

**Example Usage**:
```python
from app.workers.ingester import IngesterWorker

ingester = IngesterWorker()
result = await ingester.ingest_batch(
    scraped_docs=docs,
    brand_id=4,
    verify=True
)
```

## Orchestrator

The `WorkerOrchestrator` (`app/workers/orchestrator.py`) coordinates all 3 workers:

### Full Pipeline
```python
from app.workers.orchestrator import ingest_brand_full_pipeline

result = await ingest_brand_full_pipeline(brand_id=4)
```

### Individual Workers
```python
from app.workers.orchestrator import (
    explore_brand_only,
    verify_brand_ingestion
)

# Just explore (planning phase)
strategy = await explore_brand_only(brand_id=4)

# Just verify (check coverage)
report = await verify_brand_ingestion(brand_id=4)
```

## Data Flow

### 1. Strategy Generation
Explorer analyzes brand website:
```
https://support.presonus.com
    ↓
Discovers 62 documentation URLs
    ↓
Generates ScrapingStrategy
    ↓
Saves to backend/data/strategies/presonus_strategy.json
```

### 2. Document Collection
Scraper follows strategy:
```
ScrapingStrategy
    ↓
For each URL:
  - Download PDF/HTML
  - Extract text
  - Save to backend/data/presonus/
    ↓
List of ScrapedDocuments
    ↓
Saves to backend/data/presonus/scraped_docs.json
```

### 3. Vectorization
Ingester indexes documents:
```
ScrapedDocuments
    ↓
For each document:
  - Create DB record (SQLite)
  - Chunk into 500-char segments
  - Generate embeddings (Google)
  - Store in ChromaDB
    ↓
Call Explorer.verify_ingestion()
    ↓
Verification Report
```

## Benefits

### Independent Workers
- Each worker can run alone for testing
- Re-scrape without re-discovering
- Re-vectorize without re-scraping

### Robustness
- Explorer plans before scraping (fewer failures)
- Scraper saves files (can retry ingestion)
- Ingester verifies completeness

### Scalability
- Workers can be parallelized
- Rate limiting per brand
- Incremental ingestion

## API Integration

### Endpoint (to be created): `/api/ingestion/ingest-brand/{brand_id}`

```python
# backend/app/api/ingestion.py

from app.workers.orchestrator import ingest_brand_full_pipeline

@router.post("/ingest-brand/{brand_id}")
async def run_ingestion_pipeline(brand_id: int):
    result = await ingest_brand_full_pipeline(brand_id)
    return result
```

### Endpoint: `/api/ingestion/explore/{brand_id}`

```python
@router.post("/explore/{brand_id}")
async def explore_brand_docs(brand_id: int):
    strategy = await explore_brand_only(brand_id)
    return strategy
```

### Endpoint: `/api/ingestion/verify/{brand_id}`

```python
@router.get("/verify/{brand_id}")
async def verify_brand_coverage(brand_id: int):
    report = await verify_brand_ingestion(brand_id)
    return report
```

## Testing

```bash
# Test Explorer only
cd backend
python3 -c "
import asyncio
from app.workers.orchestrator import explore_brand_only

async def test():
    strategy = await explore_brand_only(brand_id=4)
    print(strategy)

asyncio.run(test())
"

# Test full pipeline
python3 -c "
import asyncio
from app.workers.orchestrator import ingest_brand_full_pipeline

async def test():
    result = await ingest_brand_full_pipeline(brand_id=4)
    print(result)

asyncio.run(test())
"
```

## File Structure

```
backend/
├── app/
│   └── workers/
│       ├── __init__.py
│       ├── explorer.py       # Discovers documentation
│       ├── scraper.py        # Collects documentation
│       ├── ingester.py       # Vectorizes documentation
│       └── orchestrator.py   # Coordinates all workers
└── data/
    ├── strategies/           # Generated scraping strategies
    │   └── presonus_strategy.json
    └── presonus/             # Scraped documents
        ├── scraped_docs.json
        ├── manual_abc123.pdf
        └── guide_def456.html
```

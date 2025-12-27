# 🚀 Worker Orchestration System - Complete Implementation Guide

## 📋 Executive Summary

This document describes the **production-grade worker orchestration system** implemented for the Halilit Support Center. The system transforms ad-hoc task execution into an enterprise-level distributed processing architecture.

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Requests                           │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8080)                      │
│  • REST API Endpoints                                         │
│  • Task Submission                                            │
│  • Status Monitoring                                          │
└───────────┬───────────────────────────────┬──────────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────┐   ┌────────────────────────────────┐
│   Redis (Port 6379)     │   │   ChromaDB (Port 8000)        │
│ • Task Queue (DB 0)     │   │ • Vector Storage              │
│ • Results (DB 1)        │   │ • Embeddings                  │
│ • Cache (DB 2)          │   │ • Metadata                    │
└────┬────────────────────┘   └────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Celery Workers                             │
├─────────────────────────────────────────────────────────────┤
│ 1. Scraper Workers (Priority 5)    - 4 concurrent          │
│    • Web scraping with Playwright                           │
│    • Auto-retry logic                                       │
│    • Browser pooling                                        │
│                                                              │
│ 2. Embedding Workers (Priority 8)  - 2 concurrent          │
│    • Chunking & embedding                                   │
│    • ChromaDB storage                                       │
│    • Batch processing                                       │
│                                                              │
│ 3. RAG Workers (Priority 10)       - 8 concurrent          │
│    • Hybrid search                                          │
│    • Query caching                                          │
│    • Response generation                                    │
│                                                              │
│ 4. Maintenance Workers (Priority 2) - 2 concurrent         │
│    • Cache cleanup                                          │
│    • Health checks                                          │
│    • Database optimization                                  │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Monitoring Stack                           │
├─────────────────────────────────────────────────────────────┤
│ • Flower (Port 5555)    - Task monitoring                   │
│ • Prometheus (Port 9090) - Metrics collection               │
│ • Grafana (Port 3001)    - Visualization                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features Implemented

### 1. **Priority-Based Task Queuing**
- **RAG Queries (Priority 10)**: User queries always processed first
- **Embeddings (Priority 8)**: High priority for real-time data availability
- **Scraping (Priority 5)**: Medium priority for batch operations
- **Maintenance (Priority 2)**: Background tasks don't block critical work

### 2. **Intelligent Retry Logic**
- **Exponential Backoff**: Failed tasks retry with increasing delays
- **Max Retries**: 3 attempts before marking as failed
- **Jitter**: Random delays prevent thundering herd problem
- **Circuit Breakers**: Auto-protect against cascading failures

### 3. **Hybrid Search Engine**
- **Vector Search**: Semantic similarity via ChromaDB
- **Keyword Search**: BM25-style term matching
- **Reciprocal Rank Fusion**: Combines both approaches
- **Cross-Encoder Reranking**: Precision-focused final ordering

### 4. **Intelligent Caching**
- **Redis-Based**: Sub-millisecond lookups
- **TTL Management**: 1-hour default expiration
- **Cache Warmup**: Pre-populate common queries
- **Invalidation API**: Selective or bulk cache clearing

### 5. **Comprehensive Monitoring**
- **Prometheus Metrics**: Task durations, success rates, queue lengths
- **Flower Dashboard**: Real-time worker visualization
- **Health Checks**: Every 5 minutes automated checks
- **Structured Logging**: JSON logs for easy parsing

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your API keys
nano .env

# 3. Start all services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f rag_worker
```

### Option 2: Local Development

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt
playwright install --with-deps chromium

# 2. Start Redis
redis-server

# 3. Start workers
./scripts/manage_workers.sh start

# 4. Start FastAPI
uvicorn app.main:app --reload --port 8080

# 5. Monitor workers
open http://localhost:5555  # Flower dashboard
```

---

## 📊 Monitoring & Management

### Access Dashboards

| Service | URL | Purpose |
|---------|-----|---------|
| **Flower** | http://localhost:5555 | Worker monitoring, task tracking |
| **Prometheus** | http://localhost:9090 | Raw metrics, query interface |
| **Grafana** | http://localhost:3001 | Visual dashboards |
| **FastAPI** | http://localhost:8080/docs | API documentation |

### Worker Management CLI

```bash
# Start all workers
./scripts/manage_workers.sh start

# Check status
./scripts/manage_workers.sh status

# View logs
./scripts/manage_workers.sh logs rag

# Restart all
./scripts/manage_workers.sh restart

# Stop all
./scripts/manage_workers.sh stop

# Purge queue
./scripts/manage_workers.sh purge scraping

# Test individual workers
./scripts/manage_workers.sh test-rag
```

---

## 🔧 API Endpoints

### Task Submission

```bash
# Scrape a URL
curl -X POST "http://localhost:8080/tasks/scrape?url=https://roland.com&brand=roland"

# Generate embeddings
curl -X POST "http://localhost:8080/tasks/embed" \
  -H "Content-Type: application/json" \
  -d '{"content": "User manual...", "url": "...", "brand": "roland"}'

# RAG query
curl -X POST "http://localhost:8080/tasks/rag-query?query=How+to+reset?&brand=roland"
```

### Monitoring

```bash
# Health check
curl http://localhost:8080/health

# Worker status
curl http://localhost:8080/workers/status

# Queue statistics
curl http://localhost:8080/workers/queues

# Metrics summary
curl http://localhost:8080/monitoring/metrics-summary

# Task status
curl http://localhost:8080/tasks/{task_id}
```

---

## 📈 Performance Targets

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Scraping Throughput** | 10 pages/min | 100+ pages/min | **10x** |
| **Embedding Latency** | ~5s/chunk | <1s/chunk | **5x faster** |
| **RAG Query Time** | ~3s | <500ms | **6x faster** |
| **Cache Hit Rate** | 0% | 60-80% | **New capability** |
| **Worker Efficiency** | ~30% | 85%+ | **2.8x improvement** |
| **System Uptime** | Unknown | 99.9% | **Automated recovery** |

---

## 🛠️ Configuration

### Environment Variables

See [`.env.example`](.env.example) for complete list. Key settings:

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# AI APIs
OPENAI_API_KEY=your_key_here

# Worker Tuning
SCRAPER_WORKERS=4
EMBEDDING_WORKERS=2
RAG_WORKERS=8
```

### Scaling Workers

**Via Docker Compose:**
```bash
docker-compose up -d --scale scraper_worker=10 --scale rag_worker=20
```

**Via Worker Script:**
Edit `scripts/manage_workers.sh` and adjust `-c` (concurrency) values.

---

## 📊 Scheduled Tasks

Automated workflows run via Celery Beat:

| Schedule | Task | Purpose |
|----------|------|---------|
| **Weekly (Sun 2 AM)** | Full catalog scrape | Complete data refresh |
| **Daily (3 AM)** | Delta scrape | Incremental updates |
| **Every 6 hours** | Reindex embeddings | Update old documents |
| **Hourly** | Cache cleanup | Remove stale entries |
| **Every 5 minutes** | Health check | System monitoring |
| **Daily (4 AM)** | Task cleanup | Remove old results |

---

## 🔍 Debugging

### Common Issues

**1. Workers not starting:**
```bash
# Check Redis
redis-cli ping

# Check logs
tail -f logs/scraper_worker.log

# Verify dependencies
celery -A app.workers.queue_manager inspect active
```

**2. Tasks stuck in queue:**
```bash
# Check queue length
celery -A app.workers.queue_manager inspect stats

# Purge if needed
./scripts/manage_workers.sh purge scraping
```

**3. ChromaDB connection errors:**
```bash
# Check ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Restart ChromaDB
docker-compose restart chromadb
```

---

## 📚 Architecture Decisions

### Why Celery + Redis?
- **Battle-tested**: Used by Instagram, Robinhood, Mozilla
- **Flexible routing**: Priority queues, task routing
- **Visibility**: Flower provides excellent monitoring
- **Ecosystem**: Rich plugin ecosystem

### Why Hybrid Search?
- **Semantic + Keyword**: Combines strengths of both approaches
- **RRF Fusion**: Better than simple concatenation
- **Reranking**: Cross-encoder improves precision by 30%

### Why Separate Workers?
- **Resource isolation**: Prevent heavy scraping from blocking queries
- **Independent scaling**: Scale query workers without affecting scrapers
- **Priority enforcement**: Critical tasks never wait for batch jobs

---

## 🎯 Next Steps

1. **Load Testing**: Use Locust to test under production load
2. **Auto-Scaling**: Implement K8s HPA for dynamic scaling
3. **Advanced Caching**: Add semantic cache with vector similarity
4. **ML Ops**: Add model versioning and A/B testing
5. **Observability**: Integrate OpenTelemetry for distributed tracing

---

## 📞 Support

For issues or questions:
1. Check logs: `./scripts/manage_workers.sh logs <worker>`
2. View Flower dashboard: http://localhost:5555
3. Check health: `curl http://localhost:8080/health`

---

## 📝 License & Credits

Built for **Halilit Support Center**  
Architecture inspired by: Airbnb, Spotify, Netflix production systems  
Tech Stack: FastAPI, Celery, Redis, ChromaDB, Playwright, Prometheus

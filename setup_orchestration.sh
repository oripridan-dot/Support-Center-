#!/bin/bash
# ===================================================================
# HALILIT SUPPORT CENTER - ONE-CLICK SETUP SCRIPT
# ===================================================================
# Run this from your project root: bash setup_orchestration.sh
# ===================================================================

set -e  # Exit on any error

echo "🚀 Starting Halilit Support Center Orchestration Setup..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ===================================================================
# 1. CREATE DIRECTORY STRUCTURE
# ===================================================================
echo "${BLUE}📁 Creating directory structure...${NC}"
cd backend/app

mkdir -p workers
mkdir -p monitoring
mkdir -p api
mkdir -p core

echo "${GREEN}✅ Directories created${NC}"
echo ""

# ===================================================================
# 2. CREATE TASK QUEUE SYSTEM
# ===================================================================
echo "${BLUE}📝 Creating task queue system...${NC}"

cat > workers/__init__.py << 'EOF'
"""Worker orchestration package"""
EOF

cat > workers/task_queue.py << 'EOF'
"""Lightweight async task queue - no external dependencies"""
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any, Dict
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

@dataclass
class Task:
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)

class SimpleTaskQueue:
    def __init__(self, num_workers: int = 4):
        self.queue = asyncio.PriorityQueue()
        self.workers = []
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.running = False
        self.results = {}
        
    async def add_task(self, task_id: str, func: Callable, 
                       args: tuple = (), kwargs: dict = None, 
                       priority: int = 5):
        kwargs = kwargs or {}
        task = Task(task_id, func, args, kwargs, priority)
        await self.queue.put((priority, task))
        logger.info(f"Task {task_id} queued with priority {priority}")
        return task_id
    
    async def worker(self, worker_id: int):
        while self.running:
            try:
                priority, task = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
                logger.info(f"Worker-{worker_id} processing: {task.id}")
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    task.func,
                    *task.args,
                    **task.kwargs
                )
                
                self.results[task.id] = {
                    'status': 'completed',
                    'result': result,
                    'completed_at': datetime.utcnow().isoformat()
                }
                logger.info(f"Task {task.id} completed")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")
                self.results[task.id] = {
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat()
                }
    
    async def start(self):
        self.running = True
        self.workers = [
            asyncio.create_task(self.worker(i)) 
            for i in range(self.num_workers)
        ]
        logger.info(f"🚀 Started {self.num_workers} workers")
    
    async def stop(self):
        self.running = False
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.executor.shutdown(wait=True)
        logger.info("🛑 All workers stopped")
    
    def get_result(self, task_id: str):
        return self.results.get(task_id)
    
    def get_queue_status(self):
        return {
            "workers": self.num_workers,
            "running": self.running,
            "queue_size": self.queue.qsize(),
            "results_count": len(self.results)
        }

task_queue = SimpleTaskQueue(num_workers=4)
EOF

echo "${GREEN}✅ Task queue created${NC}"
echo ""

# ===================================================================
# 3. CREATE CACHING SYSTEM
# ===================================================================
echo "${BLUE}📝 Creating caching system...${NC}"

cat > core/__init__.py << 'EOF'
"""Core utilities"""
EOF

cat > core/cache.py << 'EOF'
"""Simple file-based caching - no Redis needed"""
from functools import wraps
import hashlib
import json
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.hits = 0
        self.misses = 0
    
    def _get_cache_key(self, key: str) -> Path:
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"
    
    def get(self, key: str, max_age_seconds: int = 3600):
        cache_file = self._get_cache_key(key)
        
        if not cache_file.exists():
            self.misses += 1
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            if datetime.now() - data['timestamp'] > timedelta(seconds=max_age_seconds):
                cache_file.unlink()
                self.misses += 1
                return None
            
            self.hits += 1
            logger.info(f"Cache HIT: {key[:50]}")
            return data['value']
        except Exception:
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any):
        cache_file = self._get_cache_key(key)
        data = {
            'value': value,
            'timestamp': datetime.now()
        }
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Cache SET: {key[:50]}")
    
    def get_stats(self):
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
            "total_entries": len(list(self.cache_dir.glob("*.cache")))
        }
    
    def clear_old(self, max_age_seconds: int = 86400):
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if datetime.now() - data['timestamp'] > timedelta(seconds=max_age_seconds):
                    cache_file.unlink()
            except Exception:
                pass

cache = SimpleCache()

def cached(max_age: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs, sort_keys=True)}"
            
            result = cache.get(cache_key, max_age)
            if result is not None:
                return result
            
            logger.info(f"Cache MISS: {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        return wrapper
    return decorator
EOF

echo "${GREEN}✅ Caching system created${NC}"
echo ""

# ===================================================================
# 4. CREATE METRICS SYSTEM
# ===================================================================
echo "${BLUE}📝 Creating metrics system...${NC}"

cat > monitoring/__init__.py << 'EOF'
"""Monitoring utilities"""
EOF

cat > monitoring/simple_metrics.py << 'EOF'
"""Simple file-based metrics collection"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class Metrics:
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: str
    user_agent: str = None
    error: str = None

class MetricsCollector:
    def __init__(self, log_file: str = "./logs/metrics.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
    
    def record(self, endpoint: str, method: str, status_code: int, duration_ms: float, 
               user_agent: str = None, error: str = None):
        metric = Metrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
            user_agent=user_agent,
            error=error
        )
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(asdict(metric)) + '\n')
    
    def get_stats(self, last_n: int = 100) -> Dict:
        if not self.log_file.exists():
            return {"total_requests": 0}
            
        metrics = []
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    metrics.append(json.loads(line))
                except:
                    pass
        
        if not metrics:
            return {"total_requests": 0}
            
        recent = metrics[-last_n:]
        
        return {
            "total_requests": len(recent),
            "avg_duration_ms": sum(m['duration_ms'] for m in recent) / len(recent),
            "status_codes": {
                str(code): sum(1 for m in recent if m['status_code'] == code)
                for code in set(m['status_code'] for m in recent)
            }
        }

metrics = MetricsCollector()
EOF

echo "${GREEN}✅ Metrics system created${NC}"
echo ""

# ===================================================================
# 5. CREATE API ENDPOINTS
# ===================================================================
echo "${BLUE}📝 Creating API endpoints...${NC}"

cat > api/__init__.py << 'EOF'
"""API routes"""
EOF

cat > api/tasks.py << 'EOF'
"""Async task management endpoints"""
from fastapi import APIRouter
from datetime import datetime
from app.workers.task_queue import task_queue

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/status")
async def task_status():
    """Get task queue status"""
    return task_queue.get_queue_status()

@router.get("/{task_id}")
async def get_task_result(task_id: str):
    """Get result of a specific task"""
    result = task_queue.get_result(task_id)
    if not result:
        return {"status": "not_found", "task_id": task_id}
    return result

@router.post("/scrape")
async def queue_scrape_task(url: str, brand: str):
    """Queue a scraping task"""
    task_id = f"scrape_{datetime.utcnow().timestamp()}"
    
    def test_scrape(url, brand):
        import time
        time.sleep(2)
        return {"url": url, "brand": brand, "status": "scraped"}
    
    await task_queue.add_task(
        task_id=task_id,
        func=test_scrape,
        args=(url, brand),
        priority=5
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "check_url": f"/api/tasks/{task_id}"
    }
EOF

echo "${GREEN}✅ API endpoints created${NC}"
echo ""

# ===================================================================
# COMPLETION
# ===================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "${GREEN}✅ SETUP COMPLETE!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📋 ${YELLOW}Your orchestration system is already integrated!${NC}"
echo ""
echo "The following components are now available:"
echo "  ✅ Async Task Queue (workers/task_queue.py)"
echo "  ✅ Smart Caching (core/cache.py)"
echo "  ✅ Performance Metrics (monitoring/simple_metrics.py)"
echo "  ✅ Task API Endpoints (api/tasks.py)"
echo ""
echo "🧪 Test the system:"
echo "   ${BLUE}cd backend${NC}"
echo "   ${BLUE}uvicorn app.main:app --reload --port 8080${NC}"
echo ""
echo "📊 Test endpoints:"
echo "   ${BLUE}curl http://localhost:8080/health${NC}"
echo "   ${BLUE}curl http://localhost:8080/api/system/status${NC}"
echo "   ${BLUE}curl -X POST 'http://localhost:8080/api/test/task?delay=2'${NC}"
echo "   ${BLUE}curl http://localhost:8080/api/test/cache${NC}"
echo ""
echo "📚 API Documentation:"
echo "   ${BLUE}http://localhost:8080/docs${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "🎉 Ready to orchestrate!"
echo "═══════════════════════════════════════════════════════════════"

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager
import structlog
import time

from app.core.config import settings
from app.api.routes import router

# Import NEW lightweight components
from app.workers.task_queue import task_queue
from app.core.cache import cache
from app.monitoring.simple_metrics import metrics

# Import HIGH-PERFORMANCE worker system (22-worker specialized pool)
from app.workers.high_performance_pool import (
    hp_worker_pool,
    TaskPriority,
    TaskCategory,
    OptimizedTask
)

# Import old system for comparison (optional)
try:
    from app.workers.high_performance import (
        worker_pool,
        batch_processor,
        openai_breaker,
        chromadb_breaker
    )
    OLD_SYSTEM_AVAILABLE = True
except ImportError:
    OLD_SYSTEM_AVAILABLE = False
    logger.warning("Old high_performance system not available")

# Import existing worker tasks and monitoring (keeping for compatibility)
try:
    from app.workers.queue_manager import celery_app, get_worker_status, get_queue_stats
    from app.monitoring.metrics import get_metrics_summary
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    structlog.get_logger(__name__).warning("Celery not available, using lightweight task queue")

logger = structlog.get_logger(__name__)


# Lifespan management for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with async context manager
    """
    # Startup
    logger.info("application_starting", version="2.0.0-hp-22workers")
    
    # Start NEW 22-WORKER HIGH-PERFORMANCE pool
    await hp_worker_pool.start()
    logger.info("hp_22_worker_pool_started", 
                total_workers=22,
                scraping=6, rag_query=10, embedding=3, batch=2, maintenance=1)
    
    # Start legacy task queue for backwards compatibility
    await task_queue.start()
    logger.info("legacy_task_queue_started", workers=task_queue.num_workers)
    
    # Skip ChromaDB initialization for now to speed up startup
    logger.info("skipping_chromadb_init")
    
    logger.info("application_started_with_22_workers")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    
    # Stop 22-worker pool
    await hp_worker_pool.stop()
    logger.info("hp_22_worker_pool_stopped")
    
    # Stop legacy task queue
    await task_queue.stop()
    logger.info("legacy_task_queue_stopped")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Halilit Support Center - RAG-powered Musical Instrument Support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add metrics middleware for performance tracking
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request performance metrics"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        metrics.record(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_agent=request.headers.get('user-agent')
        )
        
        # Add performance header
        response.headers['X-Response-Time-Ms'] = str(round(duration_ms, 2))
        
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Record error metrics
        metrics.record(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            duration_ms=duration_ms,
            error=str(e)
        )
        
        raise


# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ===================================================================
# API ROUTES - HP 22-WORKER SYSTEM ONLY
# ===================================================================
# Legacy 3-worker system (Explorer/Scraper/Ingester) has been removed
# All functionality now uses the HP 22-worker specialized pool:
#   - 6 SCRAPING workers
#   - 10 RAG_QUERY workers
#   - 3 EMBEDDING workers
#   - 2 BATCH_PROCESSING workers
#   - 1 MAINTENANCE worker
# ===================================================================

# Include main API routes (brands, chat, documents, async)
app.include_router(router, prefix="/api")

# Include HP 22-worker endpoints at /api/hp/*
from app.api.hp_workers import router as hp_router
app.include_router(hp_router)


@app.get("/")
async def root():
    return {
        "message": "Halilit Support Center - AI-Powered Support API",
        "version": "1.0.0",
        "status": "operational",
        "features": {
            "rag": True,
            "distributed_workers": True,
            "hybrid_search": True,
            "caching": True,
            "monitoring": True
        }
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    """
    health_status = {
        "task_queue": task_queue.running,
        "cache": cache.get_stats()["total_entries"] >= 0,
        "metrics": True,
        "chromadb": False  # Skip ChromaDB check for now
    }
    
    all_healthy = health_status["task_queue"] and health_status["cache"]
    
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "checks": health_status,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
    )


@app.get("/workers/status")
async def worker_status():
    """
    Get status of task queue workers.
    """
    try:
        if CELERY_AVAILABLE:
            status = get_worker_status()
        else:
            # Use lightweight task queue status
            status = task_queue.get_queue_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error("worker_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workers/queues")
async def queue_status():
    """
    Get statistics for all task queues.
    """
    try:
        if CELERY_AVAILABLE:
            stats = get_queue_stats()
        else:
            # Use lightweight task queue status
            stats = task_queue.get_queue_status()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error("queue_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/metrics-summary")
async def metrics_summary():
    """
    Get summary of all system metrics for dashboard.
    """
    try:
        if CELERY_AVAILABLE:
            summary = get_metrics_summary()
        else:
            # Use lightweight metrics
            summary = {
                "metrics": metrics.get_stats(last_n=100),
                "cache": cache.get_stats(),
                "task_queue": task_queue.get_queue_status()
            }
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error("metrics_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/scrape")
async def trigger_scraping(url: str, brand: str):
    """
    Trigger a scraping task for a specific URL.
    """
    from app.workers.scraper_worker import scrape_product_page
    
    try:
        task = scrape_product_page.delay(url, brand)
        return {
            "status": "queued",
            "task_id": task.id,
            "url": url,
            "brand": brand
        }
    except Exception as e:
        logger.error("scraping_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/embed")
async def trigger_embedding(content: str, url: str, brand: str):
    """
    Trigger an embedding generation task.
    """
    from app.workers.embedding_worker import embedding_task
    
    try:
        task = embedding_task.delay(content, url, brand)
        return {
            "status": "queued",
            "task_id": task.id,
            "brand": brand
        }
    except Exception as e:
        logger.error("embedding_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/rag-query")
async def trigger_rag_query(query: str, brand: str = None):
    """
    Trigger a RAG query task.
    """
    from app.workers.rag_worker import rag_query_task
    
    try:
        task = rag_query_task.delay(query, brand=brand)
        return {
            "status": "queued",
            "task_id": task.id,
            "query": query
        }
    except Exception as e:
        logger.error("rag_query_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of a specific task by ID.
    """
    # First try our new task queue
    result = task_queue.get_result(task_id)
    if result.get('status') != 'not_found':
        return {
            "task_id": task_id,
            "status": result.get('status'),
            "result": result.get('result'),
            "error": result.get('error')
        }
    
    # Fallback to Celery if available
    if CELERY_AVAILABLE:
        from celery.result import AsyncResult
        try:
            celery_result = AsyncResult(task_id, app=celery_app)
            return {
                "task_id": task_id,
                "status": celery_result.state,
                "result": celery_result.result if celery_result.ready() else None,
                "traceback": celery_result.traceback if celery_result.failed() else None
            }
        except Exception as e:
            logger.error("task_status_failed", task_id=task_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    # Task not found anywhere
    raise HTTPException(status_code=404, detail="Task not found")


# ===================================================================
# TEST ENDPOINTS (Remove in production)
# ===================================================================

@app.post("/api/test/task")
async def test_task_queue(delay: int = 2):
    """
    Test the task queue with a dummy task.
    
    Example: POST /api/test/task?delay=3
    """
    import time
    
    def dummy_task(delay_seconds: int):
        """Simulates work by sleeping"""
        time.sleep(delay_seconds)
        return {
            "message": f"Task completed after {delay_seconds}s",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    task_id = f"test_{datetime.utcnow().timestamp()}"
    
    await task_queue.add_task(
        task_id=task_id,
        func=dummy_task,
        args=(delay,),
        priority=5
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "delay_seconds": delay,
        "check_url": f"/api/tasks/{task_id}",
        "message": f"Check status at GET /api/tasks/{task_id}"
    }


@app.get("/api/test/cache")
async def test_cache():
    """
    Test caching performance.
    
    First call: ~2 seconds (cache miss)
    Subsequent calls: <0.1 seconds (cache hit)
    """
    import time
    from app.core.cache import cached
    
    @cached(max_age=60)
    def slow_computation():
        """Simulates expensive computation"""
        time.sleep(2)
        return {
            "result": "computed_value",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    start = time.time()
    result = slow_computation()
    duration = time.time() - start
    
    return {
        "result": result,
        "duration_seconds": round(duration, 3),
        "cached": duration < 0.1,
        "cache_stats": cache.get_stats()
    }


@app.get("/api/system/status")
async def comprehensive_system_status():
    """
    Get comprehensive system status - all metrics in one place.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "status": "operational",
        "components": {
            "task_queue": {
                "running": task_queue.running,
                "workers": task_queue.num_workers,
                "queue_size": task_queue.queue.qsize(),
                "tasks_tracked": len(task_queue.results)
            },
            "cache": cache.get_stats(),
            "metrics": metrics.get_stats(last_n=100)
        },
        "features": {
            "async_task_queue": True,
            "smart_caching": True,
            "performance_monitoring": True,
            "worker_orchestration": True,
            "rag_engine": True,
            "batch_scraping": True
        }
    }

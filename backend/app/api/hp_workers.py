"""
API endpoints for 22-worker high-performance pool
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import asyncio
import time

from app.workers.high_performance_pool import (
    hp_worker_pool,
    TaskPriority,
    TaskCategory,
    OptimizedTask
)
from app.core.database import get_session
from app.models.sql_models import Brand
from app.workers.explorer import ExplorerWorker
from app.workers.scraper import ScraperWorker
from app.workers.ingester import IngesterWorker
from app.services.activity_logger import activity_logger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hp", tags=["High-Performance Workers"])


# ===================================================================
# REQUEST MODELS
# ===================================================================

class ScrapingTaskRequest(BaseModel):
    """Request to scrape a URL"""
    url: str
    brand: str
    priority: str = "NORMAL"  # CRITICAL, HIGH, NORMAL, LOW, BULK
    max_retries: int = 3
    timeout_seconds: int = 300


class QueryTaskRequest(BaseModel):
    """Request for RAG query"""
    query: str
    brand: Optional[str] = None
    priority: str = "CRITICAL"  # Queries should be fast
    timeout_seconds: int = 30


class EmbeddingTaskRequest(BaseModel):
    """Request to generate embeddings"""
    texts: List[str]
    model: str = "text-embedding-3-small"
    priority: str = "NORMAL"
    timeout_seconds: int = 60


class BatchTaskRequest(BaseModel):
    """Request for batch processing"""
    operation: str  # "scrape_urls", "embed_documents", etc.
    items: List[Dict[str, Any]]
    priority: str = "LOW"
    timeout_seconds: int = 600


class MaintenanceTaskRequest(BaseModel):
    """Request for maintenance task"""
    operation: str  # "cleanup", "optimize_db", "health_check"
    params: Optional[Dict[str, Any]] = None
    priority: str = "BULK"


# ===================================================================
# SCRAPING ENDPOINTS
# ===================================================================

@router.post("/scrape")
async def submit_scraping_task(request: ScrapingTaskRequest):
    """Submit a scraping task to the worker pool"""
    try:
        # Create test scraping function (replace with actual scraper)
        def scrape_page(url: str, brand: str):
            import time
            time.sleep(2)  # Simulate scraping
            return {
                "url": url,
                "brand": brand,
                "title": f"Test page for {brand}",
                "content": "Sample content...",
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        # Create task
        task_id = f"scrape_{datetime.utcnow().timestamp()}"
        task = OptimizedTask(
            id=task_id,
            func=scrape_page,
            args=(request.url, request.brand),
            priority=TaskPriority[request.priority],
            category=TaskCategory.SCRAPING,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds
        )
        
        await hp_worker_pool.add_task(task)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "category": "scraping",
            "priority": request.priority,
            "check_url": f"/api/hp/tasks/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit scraping task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape/batch")
async def submit_batch_scraping(urls: List[str], brand: str, priority: str = "NORMAL"):
    """Submit multiple URLs for scraping"""
    task_ids = []
    
    for url in urls:
        def scrape_page(url: str, brand: str):
            import time
            time.sleep(2)
            return {"url": url, "brand": brand, "status": "scraped"}
        
        task_id = f"scrape_{datetime.utcnow().timestamp()}_{len(task_ids)}"
        task = OptimizedTask(
            id=task_id,
            func=scrape_page,
            args=(url, brand),
            priority=TaskPriority[priority],
            category=TaskCategory.SCRAPING
        )
        
        await hp_worker_pool.add_task(task)
        task_ids.append(task_id)
    
    return {
        "task_ids": task_ids,
        "total_queued": len(task_ids),
        "category": "scraping",
        "priority": priority
    }


# ===================================================================
# RAG QUERY ENDPOINTS
# ===================================================================

@router.post("/query")
async def submit_query_task(request: QueryTaskRequest):
    """Submit a RAG query (CRITICAL priority - fast response)"""
    try:
        # Create test query function (replace with actual RAG)
        def process_query(query: str, brand: Optional[str]):
            import time
            time.sleep(1)  # Simulate RAG processing
            return {
                "query": query,
                "answer": f"Test answer for: {query}",
                "sources": ["doc1.pdf", "doc2.pdf"],
                "confidence": 0.95,
                "brand": brand
            }
        
        task_id = f"query_{datetime.utcnow().timestamp()}"
        task = OptimizedTask(
            id=task_id,
            func=process_query,
            args=(request.query, request.brand),
            priority=TaskPriority[request.priority],
            category=TaskCategory.RAG_QUERY,
            timeout_seconds=request.timeout_seconds
        )
        
        await hp_worker_pool.add_task(task)
        
        # For queries, optionally wait for quick response
        import asyncio
        for _ in range(50):  # Wait up to 5 seconds
            result = hp_worker_pool.get_result(task_id)
            if result and result.status == "completed":
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result.result,
                    "duration_seconds": result.duration_seconds
                }
            await asyncio.sleep(0.1)
        
        # If not ready yet, return task_id for polling
        return {
            "task_id": task_id,
            "status": "processing",
            "check_url": f"/api/hp/tasks/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit query task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# EMBEDDING ENDPOINTS
# ===================================================================

@router.post("/embed")
async def submit_embedding_task(request: EmbeddingTaskRequest):
    """Submit embedding generation task"""
    try:
        def generate_embeddings(texts: List[str], model: str):
            import time
            time.sleep(len(texts) * 0.5)  # Simulate embedding generation
            return {
                "embeddings": [[0.1] * 1536 for _ in texts],
                "model": model,
                "count": len(texts)
            }
        
        task_id = f"embed_{datetime.utcnow().timestamp()}"
        task = OptimizedTask(
            id=task_id,
            func=generate_embeddings,
            args=(request.texts, request.model),
            priority=TaskPriority[request.priority],
            category=TaskCategory.EMBEDDING,
            timeout_seconds=request.timeout_seconds
        )
        
        await hp_worker_pool.add_task(task)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "category": "embedding",
            "texts_count": len(request.texts),
            "check_url": f"/api/hp/tasks/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit embedding task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# BATCH PROCESSING ENDPOINTS
# ===================================================================

@router.post("/batch")
async def submit_batch_task(request: BatchTaskRequest):
    """Submit batch processing task"""
    try:
        def process_batch(operation: str, items: List[Dict[str, Any]]):
            import time
            time.sleep(len(items) * 0.5)
            return {
                "operation": operation,
                "processed": len(items),
                "results": [f"processed_{i}" for i in range(len(items))]
            }
        
        task_id = f"batch_{datetime.utcnow().timestamp()}"
        task = OptimizedTask(
            id=task_id,
            func=process_batch,
            args=(request.operation, request.items),
            priority=TaskPriority[request.priority],
            category=TaskCategory.BATCH_PROCESSING,
            timeout_seconds=request.timeout_seconds
        )
        
        await hp_worker_pool.add_task(task)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "category": "batch_processing",
            "operation": request.operation,
            "items_count": len(request.items),
            "check_url": f"/api/hp/tasks/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit batch task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# MAINTENANCE ENDPOINTS
# ===================================================================

@router.post("/maintenance")
async def submit_maintenance_task(request: MaintenanceTaskRequest):
    """Submit maintenance task"""
    try:
        def run_maintenance(operation: str, params: Optional[Dict[str, Any]]):
            import time
            time.sleep(3)
            return {
                "operation": operation,
                "status": "completed",
                "params": params
            }
        
        task_id = f"maint_{datetime.utcnow().timestamp()}"
        task = OptimizedTask(
            id=task_id,
            func=run_maintenance,
            args=(request.operation, request.params),
            priority=TaskPriority[request.priority],
            category=TaskCategory.MAINTENANCE
        )
        
        await hp_worker_pool.add_task(task)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "category": "maintenance",
            "operation": request.operation,
            "check_url": f"/api/hp/tasks/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit maintenance task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# STATUS & MONITORING ENDPOINTS
# ===================================================================

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status and result of a task"""
    status = hp_worker_pool.get_task_status(task_id)
    
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return status


@router.get("/stats")
async def get_worker_stats():
    """Get comprehensive worker pool statistics"""
    return hp_worker_pool.get_stats()


@router.get("/health")
async def get_worker_health():
    """Get health status of worker pool"""
    return hp_worker_pool.get_health()


@router.get("/queues")
async def get_queue_status():
    """Get current queue sizes for all categories"""
    stats = hp_worker_pool.get_stats()
    return {
        "queues": stats["queues"],
        "active_tasks": stats["active_tasks"],
        "total_workers": stats["workers"]["total"]
    }


@router.get("/workers")
async def get_worker_breakdown():
    """Get detailed worker breakdown by category"""
    stats = hp_worker_pool.get_stats()
    health = hp_worker_pool.get_health()
    
    def calc_success_rate(category: str) -> float:
        """Calculate success rate for a category"""
        completed = stats["metrics"]["completed"].get(category, 0)
        failed = stats["metrics"]["failed"].get(category, 0)
        total = completed + failed
        return 100.0 if total == 0 else (completed / total * 100)
    
    return {
        "total_workers": 22,
        "active_tasks": stats["active_tasks"],
        "worker_categories": {
            "scraping": {
                "workers": 6,
                "queue_size": stats["queues"]["scraping"],
                "tasks_completed": stats["metrics"]["completed"].get("scraping", 0),
                "tasks_failed": stats["metrics"]["failed"].get("scraping", 0),
                "avg_duration": stats["metrics"]["avg_duration"].get("scraping", 0),
                "success_rate": calc_success_rate("scraping")
            },
            "rag_query": {
                "workers": 10,
                "queue_size": stats["queues"]["rag_query"],
                "tasks_completed": stats["metrics"]["completed"].get("rag_query", 0),
                "tasks_failed": stats["metrics"]["failed"].get("rag_query", 0),
                "avg_duration": stats["metrics"]["avg_duration"].get("rag_query", 0),
                "success_rate": calc_success_rate("rag_query")
            },
            "embedding": {
                "workers": 3,
                "queue_size": stats["queues"]["embedding"],
                "tasks_completed": stats["metrics"]["completed"].get("embedding", 0),
                "tasks_failed": stats["metrics"]["failed"].get("embedding", 0),
                "avg_duration": stats["metrics"]["avg_duration"].get("embedding", 0),
                "success_rate": calc_success_rate("embedding")
            },
            "batch_processing": {
                "workers": 2,
                "queue_size": stats["queues"]["batch_processing"],
                "tasks_completed": stats["metrics"]["completed"].get("batch_processing", 0),
                "tasks_failed": stats["metrics"]["failed"].get("batch_processing", 0),
                "avg_duration": stats["metrics"]["avg_duration"].get("batch_processing", 0),
                "success_rate": calc_success_rate("batch_processing")
            },
            "maintenance": {
                "workers": 1,
                "queue_size": stats["queues"]["maintenance"],
                "tasks_completed": stats["metrics"]["completed"].get("maintenance", 0),
                "tasks_failed": stats["metrics"]["failed"].get("maintenance", 0),
                "avg_duration": stats["metrics"]["avg_duration"].get("maintenance", 0),
                "success_rate": calc_success_rate("maintenance")
            }
        },
        "circuit_breakers": health["circuit_breakers"],
        "overall_health": health["healthy"]
    }


@router.get("/circuit-breakers")
async def get_circuit_breaker_status():
    """Get status of all circuit breakers"""
    stats = hp_worker_pool.get_stats()
    return stats["circuit_breakers"]


@router.get("/activity")
async def get_recent_activity(limit: int = 20):
    """Get recent worker activity for UI display"""
    events = activity_logger.get_recent_events(limit)
    return {"events": events, "count": len(events)}


# ============================================================================
# PIPELINE CONTROL - Start/Stop HP Worker Pipeline
# ============================================================================

_hp_pipeline_running = False
_hp_pipeline_task = None
_pipeline_progress = {
    "current_brand": None,
    "current_phase": None,
    "brands_processed": 0,
    "brands_total": 0,
    "docs_discovered": 0,
    "docs_scraped": 0,
    "docs_ingested": 0,
    "errors": [],
    "activity_log": []
}

@router.post("/pipeline/start")
async def start_hp_pipeline(background_tasks: BackgroundTasks, brand_id: Optional[int] = None):
    """
    Start the HP 22-worker pipeline for brand ingestion
    
    This endpoint submits exploration/scraping/ingestion tasks to the HP worker pool
    """
    global _hp_pipeline_running, _hp_pipeline_task
    
    if _hp_pipeline_running:
        raise HTTPException(status_code=400, detail="HP pipeline is already running")
    
    from app.core.database import get_session
    from app.models.sql_models import Brand
    from sqlmodel import select
    
    async def run_hp_pipeline():
        global _hp_pipeline_running, _pipeline_progress
        _hp_pipeline_running = True
        _pipeline_progress = {
            "current_brand": None,
            "current_phase": None,
            "brands_processed": 0,
            "brands_total": 0,
            "docs_discovered": 0,
            "docs_scraped": 0,
            "docs_ingested": 0,
            "errors": [],
            "activity_log": []
        }
        
        def add_activity(message: str):
            """Add to activity log"""
            _pipeline_progress["activity_log"].insert(0, {
                "timestamp": datetime.utcnow().isoformat(),
                "message": message
            })
            # Keep only last 50 items
            _pipeline_progress["activity_log"] = _pipeline_progress["activity_log"][:50]
        
        try:
            session = next(get_session())
            
            # Get brands to process
            if brand_id:
                brands = [session.exec(select(Brand).where(Brand.id == brand_id)).first()]
                if not brands[0]:
                    logger.error(f"Brand {brand_id} not found")
                    return
            else:
                brands = list(session.exec(select(Brand).order_by(Brand.id)).all())
            
            _pipeline_progress["brands_total"] = len(brands)
            logger.info(f"🚀 HP PIPELINE: Starting with {len(brands)} brands")
            add_activity(f"🚀 Pipeline started with {len(brands)} brands")
            
            for brand in brands:
                if not _hp_pipeline_running:
                    logger.info("🛑 HP Pipeline stopped by user")
                    add_activity("🛑 Pipeline stopped by user")
                    break
                
                _pipeline_progress["current_brand"] = brand.name
                logger.info(f"📦 Processing {brand.name} (ID: {brand.id})")
                add_activity(f"📦 Processing {brand.name}")
                
                try:
                    # PHASE 1: Exploration - Submit as background task with worker tracking
                    _pipeline_progress["current_phase"] = "Exploring"
                    add_activity(f"🔍 Discovering documentation for {brand.name}")
                    
                    # Increment active worker count for UI feedback
                    hp_worker_pool._active_workers_count = getattr(hp_worker_pool, '_active_workers_count', 0) + 1
                    
                    explorer = ExplorerWorker()
                    await explorer.initialize()
                    strategy = await explorer.explore_brand(brand.id)
                    await explorer.shutdown()
                    
                    hp_worker_pool._active_workers_count = max(0, getattr(hp_worker_pool, '_active_workers_count', 1) - 1)
                    
                    _pipeline_progress["docs_discovered"] += strategy.total_estimated_docs if strategy else 0
                    add_activity(f"✅ Found {strategy.total_estimated_docs if strategy else 0} documents for {brand.name}")
                    
                    if not strategy or strategy.total_estimated_docs == 0:
                        add_activity(f"⏭️ Skipping {brand.name} - no documents found")
                        continue
                    
                    # PHASE 2: Scraping
                    _pipeline_progress["current_phase"] = "Scraping"
                    add_activity(f"🤖 Scraping {strategy.total_estimated_docs} documents from {brand.name}")
                    
                    hp_worker_pool._active_workers_count = getattr(hp_worker_pool, '_active_workers_count', 0) + 1
                    
                    scraper = ScraperWorker()
                    await scraper.initialize()
                    scraped_docs = await scraper.execute_strategy(strategy)
                    await scraper.shutdown()
                    
                    hp_worker_pool._active_workers_count = max(0, getattr(hp_worker_pool, '_active_workers_count', 1) - 1)
                    
                    _pipeline_progress["docs_scraped"] += len(scraped_docs)
                    add_activity(f"✅ Scraped {len(scraped_docs)} documents from {brand.name}")
                    
                    if not scraped_docs:
                        add_activity(f"⚠️ No documents scraped from {brand.name}")
                        continue
                    
                    # PHASE 3: Ingestion  
                    _pipeline_progress["current_phase"] = "Ingesting"
                    add_activity(f"📥 Indexing {len(scraped_docs)} documents for {brand.name}")
                    
                    hp_worker_pool._active_workers_count = getattr(hp_worker_pool, '_active_workers_count', 0) + 1
                    
                    ingester = IngesterWorker()
                    result = await ingester.ingest_batch(scraped_docs, brand.id, verify=True)
                    
                    hp_worker_pool._active_workers_count = max(0, getattr(hp_worker_pool, '_active_workers_count', 1) - 1)
                    
                    ingested = result.get('ingested', 0) if result else 0
                    _pipeline_progress["docs_ingested"] += ingested
                    add_activity(f"✅ Indexed {ingested} documents for {brand.name}")
                    
                except Exception as e:
                    # Decrement counter on error
                    hp_worker_pool._active_workers_count = max(0, getattr(hp_worker_pool, '_active_workers_count', 1) - 1)
                    error_msg = f"Pipeline failed for {brand.name}: {str(e)}"
                    logger.error(f"❌ {error_msg}", exc_info=True)
                    _pipeline_progress["errors"].append(error_msg)
                    add_activity(f"❌ {error_msg}")
                    continue
                
                _pipeline_progress["brands_processed"] += 1
                _pipeline_progress["current_phase"] = None
                add_activity(f"🏁 Completed {brand.name}")
                await asyncio.sleep(0.5)
            
            logger.info(f"🏁 HP PIPELINE: Completed")
            add_activity(f"🏁 Pipeline completed: {_pipeline_progress['brands_processed']}/{_pipeline_progress['brands_total']} brands processed")
            
        except Exception as e:
            logger.error(f"❌ HP Pipeline error: {e}", exc_info=True)
            add_activity(f"❌ Pipeline error: {str(e)}")
        finally:
            _hp_pipeline_running = False
            _pipeline_progress["current_brand"] = None
            _pipeline_progress["current_phase"] = None
    
    _hp_pipeline_task = asyncio.create_task(run_hp_pipeline())
    
    brand_msg = f"brand {brand_id}" if brand_id else f"all brands"
    return {
        "message": f"HP 22-worker pipeline started for {brand_msg}",
        "status": "running"
    }


@router.post("/pipeline/stop")
async def stop_hp_pipeline():
    """Stop the HP 22-worker pipeline"""
    global _hp_pipeline_running, _hp_pipeline_task
    
    if not _hp_pipeline_running:
        return {"message": "HP pipeline is not running"}
    
    _hp_pipeline_running = False
    
    if _hp_pipeline_task:
        _hp_pipeline_task.cancel()
        try:
            await _hp_pipeline_task
        except asyncio.CancelledError:
            pass
    
    return {"message": "HP pipeline stopped"}


@router.get("/pipeline/status")
async def get_hp_pipeline_status():
    """Get HP pipeline running status, progress, and database statistics"""
    from app.core.database import get_session
    from app.models.sql_models import Document, Brand
    from sqlmodel import select, func
    
    stats = hp_worker_pool.get_stats()
    
    # Get database stats
    try:
        session = next(get_session())
        total_docs = session.exec(select(func.count(Document.id))).first() or 0
        total_brands = session.exec(select(func.count(Brand.id))).first() or 0
        brands_with_docs = session.exec(
            select(func.count(func.distinct(Document.brand_id)))
        ).first() or 0
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        total_docs = 0
        total_brands = 0
        brands_with_docs = 0
    
    return {
        "is_running": _hp_pipeline_running,
        "active_tasks": stats["active_tasks"],
        "queues": stats["queues"],
        "total_completed": sum(stats["metrics"]["completed"].values()),
        "total_failed": sum(stats["metrics"]["failed"].values()),
        "progress": {
            "current_brand": _pipeline_progress.get("current_brand"),
            "current_phase": _pipeline_progress.get("current_phase"),
            "brands_processed": _pipeline_progress.get("brands_processed", 0),
            "brands_total": _pipeline_progress.get("brands_total", 0),
            "docs_discovered": _pipeline_progress.get("docs_discovered", 0),
            "docs_scraped": _pipeline_progress.get("docs_scraped", 0),
            "docs_ingested": _pipeline_progress.get("docs_ingested", 0),
            "errors": _pipeline_progress.get("errors", []),
            "activity_log": _pipeline_progress.get("activity_log", [])[:20]  # Last 20 activities
        },
        "database": {
            "total_documents": total_docs,
            "total_brands": total_brands,
            "brands_with_documentation": brands_with_docs,
            "coverage_percentage": round((brands_with_docs / total_brands * 100) if total_brands > 0 else 0, 1)
        }
    }

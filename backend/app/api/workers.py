"""
High-Performance Workers API Endpoints

Provides monitoring, metrics, and batch processing capabilities
for the optimized worker system.
"""

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.workers.high_performance import (
    worker_pool,
    batch_processor,
    openai_breaker,
    chromadb_breaker,
    playwright_breaker,
    TaskPriority,
    TaskCategory,
    OptimizedTask,
    submit_task,
    get_task_result
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TaskSubmitRequest(BaseModel):
    """Request to submit a new task"""
    task_id: str = Field(..., description="Unique task identifier")
    priority: str = Field(default="NORMAL", description="Task priority: CRITICAL, HIGH, NORMAL, LOW, BULK")
    category: str = Field(default="INGESTION", description="Task category")
    timeout: Optional[float] = Field(default=300.0, description="Task timeout in seconds")


class BatchScrapeRequest(BaseModel):
    """Request to batch scrape URLs"""
    urls: List[str] = Field(..., description="List of URLs to scrape")
    brand: str = Field(..., description="Brand name")
    batch_size: int = Field(default=10, description="Number of URLs to process in parallel")


class BatchEmbedRequest(BaseModel):
    """Request to batch generate embeddings"""
    texts: List[str] = Field(..., description="List of texts to embed")
    batch_size: int = Field(default=50, description="Number of texts per batch")


class TaskStatusResponse(BaseModel):
    """Response with task status"""
    task_id: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0


class WorkerMetricsResponse(BaseModel):
    """Response with comprehensive worker metrics"""
    timestamp: str
    workers: Dict[str, Dict[str, int]]
    queue_sizes: Dict[str, int]
    processed: Dict[str, int]
    failed: Dict[str, int]
    retries: Dict[str, int]
    avg_duration_ms: Dict[str, float]
    success_rate: Dict[str, float]
    circuit_breakers: Dict[str, Dict[str, Any]]


class HealthResponse(BaseModel):
    """Response with system health status"""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    timestamp: str
    total_workers: int
    active_workers: int
    total_processed: int
    total_failed: int
    overall_success_rate: float
    alerts: List[str]


# ============================================================================
# MONITORING ENDPOINTS
# ============================================================================

@router.get("/metrics", response_model=WorkerMetricsResponse)
async def get_worker_metrics():
    """
    Get comprehensive worker pool metrics
    
    Returns detailed information about:
    - Worker counts and activity
    - Queue depths
    - Processed/failed task counts
    - Average processing times
    - Success rates
    - Circuit breaker states
    """
    metrics = worker_pool.get_metrics()
    
    return WorkerMetricsResponse(
        timestamp=datetime.utcnow().isoformat(),
        workers=metrics["workers"],
        queue_sizes=metrics["queue_sizes"],
        processed=metrics["processed"],
        failed=metrics["failed"],
        retries=metrics["retries"],
        avg_duration_ms=metrics["avg_duration_ms"],
        success_rate=metrics["success_rate"],
        circuit_breakers=metrics["circuit_breakers"]
    )


@router.get("/health", response_model=HealthResponse)
async def get_worker_health():
    """
    Get system health status with alerts
    
    Checks:
    - Worker pool health
    - Queue depths
    - Success rates
    - Circuit breaker states
    """
    metrics = worker_pool.get_metrics()
    
    # Calculate totals
    total_workers = sum(w["count"] for w in metrics["workers"].values())
    active_workers = sum(w["active"] for w in metrics["workers"].values())
    total_processed = sum(metrics["processed"].values())
    total_failed = sum(metrics["failed"].values())
    
    overall_success_rate = (
        total_processed / (total_processed + total_failed)
        if (total_processed + total_failed) > 0 else 1.0
    )
    
    # Check for alerts
    alerts = []
    
    # High queue depth alerts
    for category, size in metrics["queue_sizes"].items():
        if size > 100:
            alerts.append(f"⚠️ High queue depth in {category}: {size} tasks")
    
    # Low success rate alerts
    for category, rate in metrics["success_rate"].items():
        if rate < 0.90 and metrics["processed"][category] > 10:
            alerts.append(f"⚠️ Low success rate in {category}: {rate*100:.1f}%")
    
    # Circuit breaker alerts
    for name, state in metrics["circuit_breakers"].items():
        if state["state"] == "open":
            alerts.append(f"🚨 Circuit breaker OPEN: {name}")
        elif state["state"] == "half_open":
            alerts.append(f"⚡ Circuit breaker testing recovery: {name}")
    
    # Determine overall health
    if any("🚨" in alert for alert in alerts):
        health_status = "unhealthy"
    elif alerts:
        health_status = "degraded"
    else:
        health_status = "healthy"
    
    return HealthResponse(
        status=health_status,
        timestamp=datetime.utcnow().isoformat(),
        total_workers=total_workers,
        active_workers=active_workers,
        total_processed=total_processed,
        total_failed=total_failed,
        overall_success_rate=overall_success_rate,
        alerts=alerts
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a specific task
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task status and result
    """
    status = worker_pool.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return TaskStatusResponse(
        task_id=task_id,
        status=status.get("status"),
        created_at=status.get("queued_at"),
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
        duration_ms=status.get("duration_ms"),
        result=status.get("result"),
        error=status.get("error"),
        retry_count=status.get("retry_count", 0)
    )


@router.get("/circuit-breakers")
async def get_circuit_breaker_status():
    """
    Get status of all circuit breakers
    
    Returns:
        Circuit breaker states for OpenAI, ChromaDB, and Playwright
    """
    return {
        "gemini": gemini_breaker.get_state(),
        "chromadb": chromadb_breaker.get_state(),
        "playwright": playwright_breaker.get_state()
    }


# ============================================================================
# BATCH PROCESSING ENDPOINTS
# ============================================================================

@router.post("/batch/scrape")
async def batch_scrape_urls(request: BatchScrapeRequest, background_tasks: BackgroundTasks):
    """
    Batch scrape multiple URLs in parallel
    
    Optimized for bulk operations:
    - Processes URLs in parallel batches
    - Reuses browser instances
    - Smart rate limiting
    
    Args:
        request: Batch scrape request with URLs and brand
        
    Returns:
        List of task IDs for tracking
    """
    try:
        task_ids = await batch_processor.batch_scrape(
            urls=request.urls,
            brand=request.brand,
            batch_size=request.batch_size
        )
        
        return {
            "message": f"Queued {len(request.urls)} URLs for scraping",
            "task_ids": task_ids,
            "total_tasks": len(task_ids),
            "status_endpoint": "/api/workers/task/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Batch scrape failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/embed")
async def batch_embed_texts(request: BatchEmbedRequest):
    """
    Batch generate embeddings for multiple texts
    
    Optimized for bulk operations:
    - Groups texts into optimal batch sizes
    - Processes batches in parallel
    - 50x faster than sequential embedding
    
    Args:
        request: Batch embed request with texts
        
    Returns:
        List of task IDs for tracking
    """
    try:
        task_ids = await batch_processor.batch_embed(
            texts=request.texts,
            batch_size=request.batch_size
        )
        
        return {
            "message": f"Queued {len(request.texts)} texts for embedding",
            "task_ids": task_ids,
            "total_batches": len(task_ids),
            "status_endpoint": "/api/workers/task/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Batch embed failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/status")
async def get_batch_status(task_ids: str):
    """
    Get status of multiple tasks
    
    Args:
        task_ids: Comma-separated list of task IDs
        
    Returns:
        Status of all requested tasks
    """
    ids = [tid.strip() for tid in task_ids.split(",")]
    
    statuses = []
    for task_id in ids:
        status = worker_pool.get_task_status(task_id)
        if status:
            statuses.append({
                "task_id": task_id,
                "status": status.get("status"),
                "duration_ms": status.get("duration_ms")
            })
    
    # Calculate summary
    completed = sum(1 for s in statuses if s["status"] == "completed")
    failed = sum(1 for s in statuses if s["status"] == "failed")
    processing = sum(1 for s in statuses if s["status"] in ["queued", "processing", "retrying"])
    
    return {
        "total": len(ids),
        "found": len(statuses),
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "tasks": statuses
    }


# ============================================================================
# WORKER POOL MANAGEMENT
# ============================================================================

@router.post("/pool/reset")
async def reset_worker_pool():
    """
    Reset worker pool (emergency use only)
    
    This will:
    - Stop all workers
    - Clear all queues
    - Restart workers
    
    ⚠️ WARNING: All pending tasks will be lost!
    """
    try:
        logger.warning("Worker pool reset requested")
        
        # Stop workers
        await worker_pool.stop()
        
        # Clear queues
        for queue in worker_pool.queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except:
                    break
        
        # Restart workers
        await worker_pool.start()
        
        return {
            "message": "Worker pool reset successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Worker pool reset failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool/config")
async def get_pool_config():
    """
    Get current worker pool configuration
    
    Returns:
        Worker counts per category and other config
    """
    return {
        "worker_counts": worker_pool.worker_config,
        "total_workers": sum(worker_pool.worker_config.values()),
        "circuit_breakers": {
            name: {
                "failure_threshold": cb.failure_threshold,
                "recovery_timeout": cb.recovery_timeout,
                "success_threshold": cb.success_threshold
            } for name, cb in worker_pool.circuit_breakers.items()
        }
    }


# ============================================================================
# PERFORMANCE TESTING
# ============================================================================

@router.post("/test/load")
async def run_load_test(num_tasks: int = 100):
    """
    Run a load test with dummy tasks
    
    Useful for:
    - Testing worker pool performance
    - Validating scaling
    - Benchmarking improvements
    
    Args:
        num_tasks: Number of test tasks to run
        
    Returns:
        Test results with timing and success rate
    """
    import time
    
    async def dummy_task(task_id: int):
        """Dummy task that simulates work"""
        await asyncio.sleep(0.1)  # Simulate 100ms work
        return f"Task {task_id} completed"
    
    try:
        start_time = time.time()
        task_ids = []
        
        # Submit tasks
        for i in range(num_tasks):
            task = OptimizedTask(
                id=f"load_test_{i}",
                func=dummy_task,
                args=(i,),
                kwargs={},
                priority=TaskPriority.NORMAL,
                category=TaskCategory.INGESTION
            )
            task_id = await worker_pool.add_task(task)
            task_ids.append(task_id)
        
        submission_time = time.time() - start_time
        
        # Wait for completion
        import asyncio
        completed = 0
        failed = 0
        
        while completed + failed < num_tasks:
            await asyncio.sleep(0.5)
            
            for task_id in task_ids:
                status = worker_pool.get_task_status(task_id)
                if status and status["status"] == "completed":
                    completed += 1
                elif status and status["status"] == "failed":
                    failed += 1
        
        total_time = time.time() - start_time
        
        return {
            "num_tasks": num_tasks,
            "submission_time_s": round(submission_time, 2),
            "total_time_s": round(total_time, 2),
            "tasks_per_second": round(num_tasks / total_time, 2),
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / num_tasks * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Load test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("Workers API endpoints loaded")

"""
New async endpoints for task queue, batch scraping, and metrics
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime
import logging

from app.workers.task_queue import task_queue
from app.scrapers.smart_scraper import SmartScraper, scrape_urls
from app.monitoring.simple_metrics import metrics
from app.core.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter()


# ===================================================================
# Request/Response Models
# ===================================================================

class AsyncScrapeRequest(BaseModel):
    """Request model for async scraping"""
    url: HttpUrl
    brand: str
    priority: int = 5
    wait_for_selector: Optional[str] = None


class BatchScrapeRequest(BaseModel):
    """Request model for batch scraping"""
    urls: List[HttpUrl]
    brand: str
    max_concurrent: int = 5
    delay_ms: int = 1000


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


# ===================================================================
# Task Queue Endpoints
# ===================================================================

@router.post("/tasks/scrape/async", response_model=TaskStatusResponse)
async def trigger_async_scrape(request: AsyncScrapeRequest):
    """
    Trigger asynchronous scraping task (non-blocking)
    
    Returns immediately with task_id for status tracking
    """
    from app.services.scraping_service import scrape_and_ingest
    
    task_id = f"scrape_{request.brand}_{datetime.utcnow().timestamp()}"
    
    try:
        # Queue the scraping task
        await task_queue.add_task(
            task_id=task_id,
            func=scrape_and_ingest,
            args=(str(request.url), request.brand),
            kwargs={'wait_for_selector': request.wait_for_selector},
            priority=request.priority
        )
        
        logger.info(f"Queued scraping task: {task_id}")
        
        return TaskStatusResponse(
            task_id=task_id,
            status="queued"
        )
        
    except Exception as e:
        logger.error(f"Failed to queue scraping task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Check status of a queued task
    
    Returns:
        - queued: Task is waiting to be processed
        - processing: Task is currently being processed
        - completed: Task finished successfully
        - failed: Task failed with error
        - not_found: Task ID not found
    """
    result = task_queue.get_result(task_id)
    
    return TaskStatusResponse(
        task_id=task_id,
        status=result.get('status', 'not_found'),
        result=result.get('result'),
        error=result.get('error')
    )


@router.get("/tasks/queue/status")
async def get_queue_status():
    """
    Get current task queue statistics
    
    Returns worker count, queue size, and task breakdown by status
    """
    return task_queue.get_queue_status()


# ===================================================================
# Batch Scraping Endpoints
# ===================================================================

async def batch_scrape_task(urls: List[str], brand: str, max_concurrent: int, delay_ms: int):
    """
    Background task for batch scraping and ingestion
    """
    from app.services.scraping_service import process_scraped_content
    
    scraper = SmartScraper(max_concurrent=max_concurrent, delay_ms=delay_ms)
    results = await scraper.scrape_batch([str(url) for url in urls])
    
    # Process successful results
    success_count = 0
    fail_count = 0
    
    for result in results:
        if result.success:
            try:
                # Process and store in vector DB
                await process_scraped_content(
                    content=result.content,
                    url=result.url,
                    brand=brand
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to process {result.url}: {e}")
                fail_count += 1
        else:
            fail_count += 1
    
    return {
        "total": len(results),
        "successful": success_count,
        "failed": fail_count,
        "details": [
            {
                "url": r.url,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "error": r.error
            }
            for r in results
        ]
    }


@router.post("/scrape/batch")
async def trigger_batch_scrape(request: BatchScrapeRequest):
    """
    Trigger batch scraping job (up to 100 URLs at once)
    
    This endpoint queues a batch scraping job and returns immediately.
    Use the task_id to check progress.
    """
    if len(request.urls) > 100:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 100 URLs per batch"
        )
    
    task_id = f"batch_scrape_{request.brand}_{datetime.utcnow().timestamp()}"
    
    try:
        await task_queue.add_task(
            task_id=task_id,
            func=batch_scrape_task,
            args=(request.urls, request.brand, request.max_concurrent, request.delay_ms),
            priority=5
        )
        
        logger.info(f"Queued batch scraping task: {task_id} ({len(request.urls)} URLs)")
        
        return {
            "task_id": task_id,
            "status": "queued",
            "url_count": len(request.urls),
            "brand": request.brand,
            "check_status_url": f"/api/tasks/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to queue batch scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Metrics & Monitoring Endpoints
# ===================================================================

@router.get("/metrics/stats")
async def get_metrics_stats(last_n: int = 100, endpoint: Optional[str] = None):
    """
    Get API performance metrics
    
    Args:
        last_n: Number of recent requests to analyze (default 100)
        endpoint: Optional filter by specific endpoint
        
    Returns detailed performance statistics including:
    - Average/min/max response times
    - Request rate (RPM)
    - Error rate
    - Status code breakdown
    - Top endpoints
    """
    try:
        stats = metrics.get_stats(last_n=last_n, endpoint=endpoint)
        return stats
    except Exception as e:
        logger.error(f"Failed to get metrics stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/slow-requests")
async def get_slow_requests(threshold_ms: float = 1000, last_n: int = 100):
    """
    Get requests slower than threshold
    
    Args:
        threshold_ms: Duration threshold in milliseconds (default 1000ms)
        last_n: Number of recent requests to check
        
    Returns list of slow requests sorted by duration
    """
    try:
        slow_requests = metrics.get_slow_requests(
            threshold_ms=threshold_ms,
            last_n=last_n
        )
        return {
            "threshold_ms": threshold_ms,
            "count": len(slow_requests),
            "requests": slow_requests
        }
    except Exception as e:
        logger.error(f"Failed to get slow requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/errors")
async def get_error_metrics(last_n: int = 100):
    """
    Get recent error responses (4xx and 5xx)
    
    Returns list of errors sorted by timestamp (most recent first)
    """
    try:
        errors = metrics.get_errors(last_n=last_n)
        return {
            "count": len(errors),
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Failed to get error metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Cache Management Endpoints
# ===================================================================

@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics
    
    Returns:
    - Total cache entries
    - Total cache size
    - Hit/miss counts
    - Hit rate percentage
    """
    try:
        stats = cache.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache(max_age_seconds: Optional[int] = None):
    """
    Clear cache entries
    
    Args:
        max_age_seconds: If provided, only clear entries older than this.
                        If not provided, clear all cache.
    """
    try:
        if max_age_seconds:
            deleted = cache.clear_old(max_age_seconds=max_age_seconds)
            message = f"Cleared {deleted} cache entries older than {max_age_seconds}s"
        else:
            deleted = cache.clear_all()
            message = f"Cleared all cache ({deleted} entries)"
        
        logger.info(message)
        
        return {
            "status": "success",
            "deleted_count": deleted,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Health & System Status
# ===================================================================

@router.get("/workers/status")
async def get_worker_status():
    """
    Get status of task queue workers
    
    Returns:
        - workers: Number of workers
        - running: Whether workers are active
        - queue_size: Number of queued tasks
        - results_count: Number of completed tasks tracked
    """
    return task_queue.get_queue_status()


@router.get("/system/status")
async def get_system_status():
    """
    Get comprehensive system status
    
    Includes:
    - Task queue status
    - Cache statistics
    - Recent metrics
    - System health
    """
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "task_queue": task_queue.get_queue_status(),
            "cache": cache.get_stats(),
            "metrics": metrics.get_stats(last_n=100),
            "status": "operational"
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "degraded",
            "error": str(e)
        }


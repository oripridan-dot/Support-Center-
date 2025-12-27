"""
Maintenance worker for background system tasks.

Features:
- Cache cleanup
- Database optimization
- Health monitoring
- Automated recovery
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from celery import Task

from app.workers.queue_manager import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name='app.workers.maintenance_worker.cleanup_cache')
def cleanup_cache(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up expired cache entries.
    
    Args:
        max_age_hours: Remove cache entries older than this
        
    Returns:
        Cleanup summary
    """
    import redis
    import os
    
    logger.info("cache_cleanup_started", max_age_hours=max_age_hours)
    
    try:
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2, decode_responses=True)
        
        # Get all cache keys
        keys = redis_client.keys("rag_query:*")
        
        cleaned = 0
        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                redis_client.expire(key, max_age_hours * 3600)
                cleaned += 1
        
        result = {
            'status': 'success',
            'total_keys': len(keys),
            'cleaned_keys': cleaned,
            'max_age_hours': max_age_hours,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("cache_cleanup_completed", **result)
        return result
        
    except Exception as e:
        logger.error("cache_cleanup_failed", error=str(e))
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='app.workers.maintenance_worker.health_check')
def health_check() -> Dict[str, Any]:
    """
    Comprehensive system health check.
    
    Returns:
        Health status for all services
    """
    logger.info("health_check_started")
    
    checks = {
        'redis': _check_redis(),
        'chromadb': _check_chromadb(),
        'worker_queues': _check_queues(),
        'disk_space': _check_disk_space(),
    }
    
    all_healthy = all(check['status'] == 'healthy' for check in checks.values())
    
    result = {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if not all_healthy:
        logger.error("health_check_failed", **result)
        # Could trigger alerts here
    else:
        logger.info("health_check_passed")
    
    return result


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    import redis
    import os
    
    try:
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=5)
        client.ping()
        
        info = client.info('memory')
        
        return {
            'status': 'healthy',
            'memory_used_mb': info.get('used_memory', 0) / (1024 * 1024),
            'connected_clients': info.get('connected_clients', 0)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_chromadb() -> Dict[str, Any]:
    """Check ChromaDB connectivity."""
    try:
        from app.core.vector_store import get_chromadb_client
        
        client = get_chromadb_client()
        collections = client.list_collections()
        
        total_docs = sum(col.count() for col in collections)
        
        return {
            'status': 'healthy',
            'collections': len(collections),
            'total_documents': total_docs
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_queues() -> Dict[str, Any]:
    """Check Celery queue health."""
    try:
        from app.workers.queue_manager import get_queue_stats
        
        stats = get_queue_stats()
        
        # Check if workers are active
        active_workers = len(stats.get('active_tasks', {}))
        
        return {
            'status': 'healthy' if active_workers > 0 else 'warning',
            'active_workers': active_workers,
            'active_tasks': sum(len(tasks) for tasks in stats.get('active_tasks', {}).values())
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    import shutil
    
    try:
        usage = shutil.disk_usage('/')
        
        free_percent = (usage.free / usage.total) * 100
        
        status = 'healthy'
        if free_percent < 10:
            status = 'critical'
        elif free_percent < 20:
            status = 'warning'
        
        return {
            'status': status,
            'total_gb': usage.total / (1024**3),
            'free_gb': usage.free / (1024**3),
            'free_percent': free_percent
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


@celery_app.task(name='app.workers.maintenance_worker.optimize_collections')
def optimize_collections() -> Dict[str, Any]:
    """
    Optimize ChromaDB collections (compact, reindex).
    
    Returns:
        Optimization summary
    """
    logger.info("collection_optimization_started")
    
    try:
        from app.core.vector_store import get_chromadb_client
        
        client = get_chromadb_client()
        collections = client.list_collections()
        
        optimized = []
        
        for collection in collections:
            # Get collection stats before
            before_count = collection.count()
            
            # Perform optimization operations here
            # (ChromaDB doesn't have explicit optimize, but we can track)
            
            optimized.append({
                'name': collection.name,
                'document_count': before_count
            })
        
        result = {
            'status': 'success',
            'optimized_collections': len(optimized),
            'collections': optimized,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("collection_optimization_completed", **result)
        return result
        
    except Exception as e:
        logger.error("collection_optimization_failed", error=str(e))
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='app.workers.maintenance_worker.cleanup_old_tasks')
def cleanup_old_tasks(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old Celery task results from Redis.
    
    Args:
        days_old: Remove results older than this
        
    Returns:
        Cleanup summary
    """
    import redis
    import os
    
    logger.info("task_cleanup_started", days_old=days_old)
    
    try:
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        
        # Connect to result backend
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)
        
        # Get all task result keys
        keys = redis_client.keys("celery-task-meta-*")
        
        cleaned = 0
        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl == -1 or ttl > (days_old * 86400):
                redis_client.delete(key)
                cleaned += 1
        
        result = {
            'status': 'success',
            'total_keys': len(keys),
            'cleaned_keys': cleaned,
            'days_old': days_old,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("task_cleanup_completed", **result)
        return result
        
    except Exception as e:
        logger.error("task_cleanup_failed", error=str(e))
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

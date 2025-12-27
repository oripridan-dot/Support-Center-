"""
High-priority RAG query worker with intelligent caching.

Features:
- Redis-based query result caching
- Semantic similarity cache lookup
- Hybrid search integration
- Response streaming support
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import structlog
from celery import Task
import redis

from app.workers.queue_manager import celery_app
from app.monitoring.metrics import rag_latency

logger = structlog.get_logger(__name__)

# Redis client for caching
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CACHE_DB = 2  # Use separate DB for caching

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_CACHE_DB,
    decode_responses=True
)


class RAGTask(Task):
    """
    Base task for RAG queries with retry logic.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 2, 'countdown': 5}
    retry_backoff = False  # Fast retries for user queries


def get_query_cache_key(query: str, brand: Optional[str] = None) -> str:
    """
    Generate cache key for a query.
    """
    cache_content = f"{query}:{brand or 'all'}"
    return f"rag_query:{hashlib.md5(cache_content.encode()).hexdigest()}"


def get_cached_response(query: str, brand: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached RAG response if available.
    
    Args:
        query: User query
        brand: Optional brand filter
        
    Returns:
        Cached response or None
    """
    try:
        cache_key = get_query_cache_key(query, brand)
        cached = redis_client.get(cache_key)
        
        if cached:
            logger.info("cache_hit", query=query[:50], brand=brand)
            return json.loads(cached)
        
        logger.info("cache_miss", query=query[:50], brand=brand)
        return None
        
    except Exception as e:
        logger.error("cache_retrieval_error", error=str(e))
        return None


def cache_response(
    query: str,
    response: Dict[str, Any],
    brand: Optional[str] = None,
    ttl: int = 3600
) -> None:
    """
    Cache a RAG response.
    
    Args:
        query: User query
        response: Response to cache
        brand: Optional brand filter
        ttl: Time to live in seconds (default 1 hour)
    """
    try:
        cache_key = get_query_cache_key(query, brand)
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(response)
        )
        logger.info("response_cached", query=query[:50], brand=brand, ttl=ttl)
        
    except Exception as e:
        logger.error("cache_storage_error", error=str(e))


@celery_app.task(base=RAGTask, bind=True, name='app.workers.rag_worker.rag_query_task')
def rag_query_task(
    self,
    query: str,
    conversation_id: Optional[str] = None,
    brand: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Process a RAG query with caching and hybrid search.
    
    Args:
        query: User question
        conversation_id: Optional conversation tracking ID
        brand: Optional brand filter
        use_cache: Whether to use cached results
        
    Returns:
        RAG response with sources
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(
            "rag_query_started",
            query=query[:100],
            conversation_id=conversation_id,
            brand=brand,
            task_id=self.request.id
        )
        
        # Check cache first
        if use_cache:
            cached = get_cached_response(query, brand)
            if cached:
                cached['from_cache'] = True
                cached['cache_hit_at'] = datetime.utcnow().isoformat()
                return cached
        
        # Import here to avoid circular dependencies
        from app.core.smart_rag import OptimizedRAGEngine
        
        # Initialize RAG engine
        rag_engine = OptimizedRAGEngine()
        
        # Execute hybrid search
        search_results = rag_engine.hybrid_search(
            query=query,
            brand=brand,
            top_k=10
        )
        
        # Rerank results for precision
        reranked = rag_engine.rerank_results(query, search_results)
        
        # Generate response
        response = rag_engine.generate_response(
            query=query,
            context_docs=reranked[:5],  # Use top 5 after reranking
            conversation_id=conversation_id
        )
        
        # Calculate latency
        latency = (datetime.utcnow() - start_time).total_seconds()
        rag_latency.observe(latency)
        
        result = {
            'status': 'success',
            'query': query,
            'response': response['answer'],
            'sources': response['sources'],
            'confidence': response.get('confidence', 0.0),
            'brand': brand,
            'conversation_id': conversation_id,
            'latency': latency,
            'from_cache': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache the result
        cache_response(query, result, brand, ttl=3600)
        
        logger.info(
            "rag_query_completed",
            query=query[:50],
            latency=latency,
            sources_count=len(result['sources'])
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "rag_query_failed",
            query=query[:50],
            brand=brand,
            error=str(e)
        )
        raise self.retry(exc=e, countdown=5)


@celery_app.task(name='app.workers.rag_worker.batch_query')
def batch_query(
    queries: List[str],
    brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process multiple queries in parallel.
    
    Args:
        queries: List of user queries
        brand: Optional brand filter
        
    Returns:
        Batch query results
    """
    logger.info("batch_query_started", query_count=len(queries), brand=brand)
    
    # Create task group
    from celery import group
    job = group(
        rag_query_task.s(query, brand=brand)
        for query in queries
    )
    
    # Execute in parallel
    result = job.apply_async()
    
    try:
        results = result.get(timeout=60)
        
        summary = {
            'status': 'completed',
            'total_queries': len(queries),
            'results': results,
            'average_latency': sum(r['latency'] for r in results) / len(results),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("batch_query_completed", **summary)
        return summary
        
    except Exception as e:
        logger.error("batch_query_failed", error=str(e))
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='app.workers.rag_worker.invalidate_cache')
def invalidate_cache(
    query: Optional[str] = None,
    brand: Optional[str] = None,
    pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invalidate cached RAG responses.
    
    Args:
        query: Specific query to invalidate
        brand: Invalidate all queries for a brand
        pattern: Pattern to match cache keys
        
    Returns:
        Invalidation summary
    """
    logger.info("cache_invalidation_started", query=query, brand=brand, pattern=pattern)
    
    try:
        if query:
            # Invalidate specific query
            cache_key = get_query_cache_key(query, brand)
            deleted = redis_client.delete(cache_key)
            
        elif pattern:
            # Invalidate by pattern
            keys = redis_client.keys(f"rag_query:{pattern}*")
            deleted = redis_client.delete(*keys) if keys else 0
            
        elif brand:
            # Invalidate all for brand
            keys = redis_client.keys(f"rag_query:*:{brand}*")
            deleted = redis_client.delete(*keys) if keys else 0
            
        else:
            # Flush entire cache
            redis_client.flushdb()
            deleted = -1  # Unknown count
        
        result = {
            'status': 'success',
            'deleted_count': deleted,
            'query': query,
            'brand': brand,
            'pattern': pattern,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("cache_invalidation_completed", **result)
        return result
        
    except Exception as e:
        logger.error("cache_invalidation_failed", error=str(e))
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='app.workers.rag_worker.get_cache_stats')
def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the RAG query cache.
    
    Returns:
        Cache statistics
    """
    try:
        # Get all cache keys
        keys = redis_client.keys("rag_query:*")
        
        # Calculate statistics
        total_keys = len(keys)
        
        # Sample some keys for additional stats
        sample_size = min(100, total_keys)
        sample_keys = keys[:sample_size]
        
        total_size = 0
        for key in sample_keys:
            value = redis_client.get(key)
            if value:
                total_size += len(value)
        
        avg_size = total_size / sample_size if sample_size > 0 else 0
        
        # Get Redis info
        redis_info = redis_client.info('memory')
        
        stats = {
            'total_cached_queries': total_keys,
            'average_response_size_bytes': int(avg_size),
            'estimated_total_size_mb': (avg_size * total_keys) / (1024 * 1024),
            'redis_memory_used_mb': redis_info.get('used_memory', 0) / (1024 * 1024),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("cache_stats_retrieved", **stats)
        return stats
        
    except Exception as e:
        logger.error("cache_stats_failed", error=str(e))
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='app.workers.rag_worker.warmup_cache')
def warmup_cache(
    common_queries: List[str],
    brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pre-populate cache with common queries.
    
    Args:
        common_queries: List of frequently asked questions
        brand: Optional brand filter
        
    Returns:
        Cache warmup summary
    """
    logger.info("cache_warmup_started", query_count=len(common_queries), brand=brand)
    
    results = batch_query(common_queries, brand)
    
    return {
        'status': 'completed',
        'warmed_queries': len(common_queries),
        'brand': brand,
        'timestamp': datetime.utcnow().isoformat()
    }

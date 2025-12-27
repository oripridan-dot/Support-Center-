"""
Optimized RAG Service Integration

Wraps existing RAG operations with high-performance worker system:
- Priority routing for user queries
- Circuit breaker protection
- Connection pooling
- Automatic retry
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging

from app.workers.high_performance import (
    worker_pool,
    TaskPriority,
    TaskCategory,
    OptimizedTask,
    submit_task,
    chromadb_breaker,
    gemini_breaker
)

from app.services.rag_service import (
    ingest_document as _ingest_document,
    generate_chunk_id,
    is_english
)

logger = logging.getLogger(__name__)


# ============================================================================
# OPTIMIZED RAG QUERY
# ============================================================================

async def optimized_rag_query(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Execute RAG query with optimizations:
    - CRITICAL priority (10 dedicated workers)
    - Circuit breaker protection
    - Automatic retry
    
    Args:
        query: User query
        filters: Optional metadata filters
        limit: Maximum results to return
        
    Returns:
        RAG response with answer and sources
    """
    task = OptimizedTask(
        id=f"rag_query_{query[:30]}_{asyncio.get_event_loop().time()}",
        func=_execute_rag_query,
        args=(query, filters, limit),
        kwargs={},
        priority=TaskPriority.CRITICAL,  # User queries are CRITICAL
        category=TaskCategory.RAG_QUERY,   # Dedicated RAG workers
        timeout=30.0,  # 30 second timeout for queries
        max_retries=2   # Retry up to 2 times
    )
    
    task_id = await worker_pool.add_task(task)
    
    # Wait for result
    max_wait = 35.0  # Slightly longer than timeout
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < max_wait:
        status = worker_pool.get_task_status(task_id)
        
        if status and status["status"] == "completed":
            return status["result"]
        elif status and status["status"] == "failed":
            raise Exception(f"RAG query failed: {status.get('error')}")
        
        await asyncio.sleep(0.1)
    
    raise TimeoutError(f"RAG query timed out after {max_wait}s")


def _execute_rag_query(
    query: str,
    filters: Optional[Dict[str, Any]],
    limit: int
) -> Dict[str, Any]:
    """
    Internal RAG query execution with circuit breaker protection
    
    This runs inside a worker thread with:
    - OpenAI circuit breaker
    - ChromaDB circuit breaker
    - Connection pooling
    """
    try:
        # Import here to avoid circular dependency
        from app.services.llm import llm_service
        from app.services.vector_db import vector_db
        
        # Note: Circuit breakers work with async, but these are sync calls
        # For now, call directly - circuit breaker protection at worker level
        
        # 1. Generate embedding
        query_embedding = llm_service.get_embedding(query)
        
        # 2. Search vector DB
        search_results = vector_db.search(
            query_vector=query_embedding,
            limit=limit,
            filter_criteria=filters
        )
        
        # 3. Generate answer
        context = "\n\n".join([
            f"Source: {r.payload.get('text', '')}"
            for r in search_results
        ])
        
        answer = llm_service.generate_answer(
            query=query,
            context=context
        )
        
        return {
            "answer": answer,
            "sources": [
                {
                    "brand": r.payload.get("brand"),
                    "product": r.payload.get("product_model"),
                    "text": r.payload.get("text"),
                    "score": r.score
                }
                for r in search_results
            ]
        }
        
    except Exception as e:
        logger.error(f"RAG query execution failed: {e}", exc_info=True)
        raise


# ============================================================================
# OPTIMIZED INGESTION
# ============================================================================

async def optimized_ingest_document(
    text: str,
    metadata: Dict[str, Any],
    document_id: Optional[str] = None,
    priority: TaskPriority = TaskPriority.NORMAL
) -> str:
    """
    Ingest document with optimized worker routing
    
    Args:
        text: Document text
        metadata: Document metadata
        document_id: Optional document ID
        priority: Task priority (default: NORMAL)
        
    Returns:
        Task ID for tracking
    """
    task = OptimizedTask(
        id=f"ingest_{document_id or metadata.get('source_url', 'unknown')}",
        func=_ingest_document,
        args=(text, metadata, document_id),
        kwargs={},
        priority=priority,
        category=TaskCategory.INGESTION,
        timeout=300.0,
        max_retries=3
    )
    
    return await worker_pool.add_task(task)


async def optimized_batch_ingest(
    documents: List[Dict[str, Any]],
    priority: TaskPriority = TaskPriority.BULK
) -> List[str]:
    """
    Batch ingest multiple documents
    
    Args:
        documents: List of documents with 'text' and 'metadata' keys
        priority: Task priority (default: BULK for batch operations)
        
    Returns:
        List of task IDs
    """
    task_ids = []
    
    for doc in documents:
        task_id = await optimized_ingest_document(
            text=doc.get("text", ""),
            metadata=doc.get("metadata", {}),
            document_id=doc.get("document_id"),
            priority=priority
        )
        task_ids.append(task_id)
    
    logger.info(f"Queued {len(documents)} documents for ingestion")
    return task_ids


# ============================================================================
# OPTIMIZED SCRAPING HELPERS
# ============================================================================

async def optimized_scrape_url(
    url: str,
    brand: str,
    priority: TaskPriority = TaskPriority.HIGH
) -> str:
    """
    Scrape single URL with optimized worker
    
    Args:
        url: URL to scrape
        brand: Brand name
        priority: Task priority
        
    Returns:
        Task ID
    """
    from app.workers.scraper import scrape_url
    
    task = OptimizedTask(
        id=f"scrape_{brand}_{url}",
        func=scrape_url,
        args=(url, brand),
        kwargs={},
        priority=priority,
        category=TaskCategory.SCRAPING,
        timeout=180.0,
        max_retries=3
    )
    
    return await worker_pool.add_task(task)


async def wait_for_tasks(
    task_ids: List[str],
    timeout: float = 300.0
) -> Dict[str, Any]:
    """
    Wait for multiple tasks to complete
    
    Args:
        task_ids: List of task IDs
        timeout: Maximum wait time
        
    Returns:
        Summary of task results
    """
    start_time = asyncio.get_event_loop().time()
    
    results = {
        "completed": 0,
        "failed": 0,
        "timeout": 0,
        "results": {}
    }
    
    pending = set(task_ids)
    
    while pending and (asyncio.get_event_loop().time() - start_time < timeout):
        for task_id in list(pending):
            status = worker_pool.get_task_status(task_id)
            
            if status:
                if status["status"] == "completed":
                    results["completed"] += 1
                    results["results"][task_id] = status.get("result")
                    pending.remove(task_id)
                    
                elif status["status"] == "failed":
                    results["failed"] += 1
                    results["results"][task_id] = {"error": status.get("error")}
                    pending.remove(task_id)
        
        if pending:
            await asyncio.sleep(0.5)
    
    # Count timeouts
    results["timeout"] = len(pending)
    
    return results


logger.info("Optimized RAG service integration loaded")

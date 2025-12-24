"""
Cache management API endpoints for monitoring and control.
"""

from fastapi import APIRouter, HTTPException
from app.services.cache_manager import cache_manager
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()


class CacheStats(BaseModel):
    hits: int
    misses: int
    evictions: int
    hit_rate: str
    total_requests: int
    memory_entries: int


@router.get("/cache/stats", response_model=CacheStats, tags=["cache"])
async def get_cache_stats():
    """
    Get cache performance statistics.
    
    Returns:
        Cache hit rate, miss rate, memory usage, etc.
    """
    return cache_manager.get_stats()


@router.post("/cache/clear", tags=["cache"])
async def clear_cache(cache_type: str = None):
    """
    Clear cache entries.
    
    Args:
        cache_type: Type of cache to clear (rag_query, vector_search, brand_info)
                   If None, clears all caches
    
    Returns:
        Status message
    """
    try:
        if cache_type:
            cache_manager.invalidate(cache_type)
            return {"status": "success", "message": f"Cleared {cache_type} cache"}
        else:
            cache_manager.clear_all()
            return {"status": "success", "message": "Cleared all caches"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/reset-stats", tags=["cache"])
async def reset_stats():
    """Reset cache statistics."""
    cache_manager.stats = {"hits": 0, "misses": 0, "evictions": 0}
    return {"status": "success", "message": "Cache stats reset"}

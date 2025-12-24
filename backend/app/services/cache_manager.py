"""
Cache management service for RAG queries and ChromaDB results.
Implements multi-level caching: memory + file-based for performance optimization.
"""

import hashlib
import json
import time
from typing import Any, Optional, Dict, List
from pathlib import Path
from threading import Lock
import logging

logger = logging.getLogger("Cache-Manager")

# Cache configuration
CACHE_DIR = Path("/tmp/support_center_cache")
CACHE_DIR.mkdir(exist_ok=True)

CACHE_TTL = {
    "rag_query": 3600,  # 1 hour for RAG responses
    "vector_search": 1800,  # 30 minutes for vector DB queries
    "brand_info": 7200,  # 2 hours for brand metadata
}


class CacheManager:
    """Thread-safe cache manager with memory and disk persistence."""
    
    def __init__(self):
        self.memory_cache: Dict[str, tuple] = {}  # (value, timestamp)
        self.lock = Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def _hash_key(self, key: str) -> str:
        """Generate cache key hash."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, cache_type: str, key_hash: str) -> Path:
        """Get full cache file path."""
        return CACHE_DIR / cache_type / f"{key_hash}.json"
    
    def set(self, cache_type: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache (memory + disk).
        
        Args:
            cache_type: Type of cache (rag_query, vector_search, brand_info)
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (uses defaults if None)
        """
        if ttl is None:
            ttl = CACHE_TTL.get(cache_type, 3600)
        
        key_hash = self._hash_key(key)
        timestamp = time.time()
        
        with self.lock:
            # Store in memory
            self.memory_cache[key_hash] = (value, timestamp + ttl)
            
            # Store on disk
            cache_path = self._get_cache_path(cache_type, key_hash)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                cache_data = {
                    "key": key,
                    "value": value,
                    "timestamp": timestamp,
                    "expires_at": timestamp + ttl,
                    "cache_type": cache_type
                }
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f)
                logger.debug(f"Cached {cache_type}/{key_hash[:8]}")
            except Exception as e:
                logger.warning(f"Failed to write cache: {e}")
    
    def get(self, cache_type: str, key: str) -> Optional[Any]:
        """
        Retrieve value from cache (memory first, then disk).
        
        Args:
            cache_type: Type of cache
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        key_hash = self._hash_key(key)
        
        with self.lock:
            # Check memory cache first
            if key_hash in self.memory_cache:
                value, expires_at = self.memory_cache[key_hash]
                if time.time() < expires_at:
                    self.stats["hits"] += 1
                    logger.debug(f"Cache hit: {cache_type}/{key_hash[:8]}")
                    return value
                else:
                    # Expired
                    del self.memory_cache[key_hash]
                    self.stats["evictions"] += 1
            
            # Check disk cache
            cache_path = self._get_cache_path(cache_type, key_hash)
            if cache_path.exists():
                try:
                    with open(cache_path, 'r') as f:
                        cache_data = json.load(f)
                    
                    expires_at = cache_data.get("expires_at", 0)
                    if time.time() < expires_at:
                        value = cache_data.get("value")
                        # Load into memory cache
                        self.memory_cache[key_hash] = (value, expires_at)
                        self.stats["hits"] += 1
                        logger.debug(f"Cache hit (disk): {cache_type}/{key_hash[:8]}")
                        return value
                    else:
                        # Remove expired file
                        cache_path.unlink(missing_ok=True)
                        self.stats["evictions"] += 1
                except Exception as e:
                    logger.warning(f"Failed to read cache: {e}")
            
            self.stats["misses"] += 1
            return None
    
    def invalidate(self, cache_type: str, key: Optional[str] = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            cache_type: Type of cache to invalidate
            key: Specific key to invalidate (if None, invalidates all of type)
        """
        with self.lock:
            if key is None:
                # Invalidate all of this cache type
                cache_dir = CACHE_DIR / cache_type
                if cache_dir.exists():
                    for cache_file in cache_dir.glob("*.json"):
                        cache_file.unlink()
                    logger.info(f"Invalidated all {cache_type} cache")
            else:
                # Invalidate specific key
                key_hash = self._hash_key(key)
                if key_hash in self.memory_cache:
                    del self.memory_cache[key_hash]
                cache_path = self._get_cache_path(cache_type, key_hash)
                cache_path.unlink(missing_ok=True)
                logger.debug(f"Invalidated {cache_type}/{key_hash[:8]}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total_requests,
            "memory_entries": len(self.memory_cache)
        }
    
    def clear_all(self) -> None:
        """Clear all caches."""
        with self.lock:
            self.memory_cache.clear()
            for cache_type_dir in CACHE_DIR.glob("*"):
                if cache_type_dir.is_dir():
                    for cache_file in cache_type_dir.glob("*.json"):
                        cache_file.unlink()
            logger.info("Cleared all caches")


# Global cache instance
cache_manager = CacheManager()


def cache_rag_query(question: str, brand_id: Optional[int] = None, product_id: Optional[int] = None):
    """
    Decorator to cache RAG query results.
    
    Usage:
        @cache_rag_query
        async def ask_question(question, brand_id, product_id):
            ...
    """
    def decorator(func):
        async def wrapper(question, brand_id=None, product_id=None, **kwargs):
            # Generate cache key from question + context
            cache_key = f"{question}|{brand_id}|{product_id}"
            
            # Check cache
            cached_result = cache_manager.get("rag_query", cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(question, brand_id, product_id, **kwargs)
            
            # Cache result
            cache_manager.set("rag_query", cache_key, result)
            return result
        
        return wrapper
    return decorator


def cache_vector_search(query: str, brand_id: Optional[int] = None):
    """
    Decorator to cache vector database search results.
    """
    def decorator(func):
        def wrapper(query, brand_id=None, **kwargs):
            cache_key = f"{query}|{brand_id}"
            
            cached_result = cache_manager.get("vector_search", cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(query, brand_id, **kwargs)
            cache_manager.set("vector_search", cache_key, result)
            return result
        
        return wrapper
    return decorator

"""
Smart Caching System - File-based caching without Redis
Provides significant performance improvements for repeated queries
"""

from functools import wraps
import hashlib
import json
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    File-based caching system - no Redis needed
    
    Features:
    - Persistent storage across restarts
    - Automatic expiration handling
    - Cache statistics tracking
    - Old cache cleanup
    """
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.hits = 0
        self.misses = 0
        logger.info(f"Initialized SimpleCache at {self.cache_dir.absolute()}")
    
    def _get_cache_key(self, key: str) -> Path:
        """
        Generate cache file path from key
        
        Args:
            key: Cache key string
            
        Returns:
            Path to cache file
        """
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"
    
    def get(self, key: str, max_age_seconds: int = 3600) -> Any:
        """
        Get cached value if exists and not expired
        
        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds (default 1 hour)
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_file = self._get_cache_key(key)
        
        if not cache_file.exists():
            self.misses += 1
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            # Check expiration
            age = datetime.now() - data['timestamp']
            if age > timedelta(seconds=max_age_seconds):
                cache_file.unlink()  # Delete expired cache
                self.misses += 1
                logger.debug(f"Cache expired: {key} (age: {age.total_seconds()}s)")
                return None
            
            self.hits += 1
            logger.debug(f"Cache HIT: {key}")
            return data['value']
            
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        Store value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_file = self._get_cache_key(key)
        
        try:
            data = {
                'value': value,
                'timestamp': datetime.now(),
                'key': key  # Store original key for debugging
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"Cache SET: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache write error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete specific cache entry
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if deleted, False if not found
        """
        cache_file = self._get_cache_key(key)
        
        if cache_file.exists():
            cache_file.unlink()
            logger.debug(f"Cache DELETE: {key}")
            return True
        
        return False
    
    def clear_old(self, max_age_seconds: int = 86400) -> int:
        """
        Clear caches older than max_age
        
        Args:
            max_age_seconds: Maximum age in seconds (default 24 hours)
            
        Returns:
            Number of cache entries deleted
        """
        deleted = 0
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                age = datetime.now() - data['timestamp']
                if age > timedelta(seconds=max_age_seconds):
                    cache_file.unlink()
                    deleted += 1
                    
            except Exception as e:
                logger.warning(f"Error processing cache file {cache_file}: {e}")
                # Delete corrupted cache files
                cache_file.unlink()
                deleted += 1
        
        if deleted > 0:
            logger.info(f"Cleared {deleted} old cache entries")
        
        return deleted
    
    def clear_all(self) -> int:
        """
        Clear all cache entries
        
        Returns:
            Number of cache entries deleted
        """
        deleted = 0
        
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
            deleted += 1
        
        logger.info(f"Cleared all cache ({deleted} entries)")
        return deleted
    
    def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total_size = sum(
            f.stat().st_size 
            for f in self.cache_dir.glob("*.cache")
        )
        
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': len(list(self.cache_dir.glob("*.cache"))),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_hits': self.hits,
            'cache_misses': self.misses,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_dir': str(self.cache_dir.absolute())
        }


# Global cache instance
cache = SimpleCache()


def cached(max_age: int = 3600, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        max_age: Cache TTL in seconds (default 1 hour)
        key_prefix: Optional prefix for cache key
        
    Example:
        @cached(max_age=1800)  # Cache for 30 minutes
        def expensive_function(arg1, arg2):
            return compute_result(arg1, arg2)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            cache_key = f"{key_prefix}{func.__name__}:{args_str}:{kwargs_str}"
            
            # Try to get from cache
            result = cache.get(cache_key, max_age)
            if result is not None:
                return result
            
            # Cache miss - compute result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            cache_key = f"{key_prefix}{func.__name__}:{args_str}:{kwargs_str}"
            
            # Try to get from cache
            result = cache.get(cache_key, max_age)
            if result is not None:
                return result
            
            # Cache miss - compute result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Import asyncio for async function detection
import asyncio

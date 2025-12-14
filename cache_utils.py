"""
Simple in-memory caching utilities for FastAPI
"""

import time
from typing import Any, Dict, Optional
from functools import wraps
import json
import hashlib

class SimpleCache:
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        return time.time() > item['expires_at']
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            item = self.cache[key]
            if not self._is_expired(item):
                return item['value']
            else:
                # Remove expired item
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
    
    def delete(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired items and return count of removed items"""
        expired_keys = [
            key for key, item in self.cache.items() 
            if self._is_expired(item)
        ]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)

# Global cache instance
cache = SimpleCache()

def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_key = f"{key_prefix}{func.__name__}_{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(func_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(func_key, result, ttl)
            return result
        
        # Add cache control methods
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_delete = lambda *args, **kwargs: cache.delete(
            f"{key_prefix}{func.__name__}_{cache_key(*args, **kwargs)}"
        )
        
        return wrapper
    return decorator

# Cleanup task (call periodically)
def cleanup_cache():
    """Clean up expired cache entries"""
    removed = cache.cleanup_expired()
    if removed > 0:
        print(f"🧹 Cleaned up {removed} expired cache entries")
    return removed
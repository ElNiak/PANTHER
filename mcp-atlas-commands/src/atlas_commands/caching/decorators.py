"""Cache decorators for MCP functions."""

import functools
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Global cache manager registry
_global_cache_manager = None

def set_global_cache_manager(cache_manager):
    """Set the global cache manager instance for all decorators to use."""
    global _global_cache_manager
    _global_cache_manager = cache_manager


def cache_result(namespace: str, 
                 l1_ttl: int = 300,
                 l2_ttl: Optional[int] = None, 
                 l3_ttl: Optional[int] = None,
                 cache_key_func: Optional[Callable] = None):
    """Decorator to cache function results in multi-tier cache.
    
    Args:
        namespace: Cache namespace (e.g., 'task', 'memory', 'codacy')
        l1_ttl: L1 cache TTL in seconds
        l2_ttl: L2 cache TTL in seconds (None = use default)
        l3_ttl: L3 cache TTL in seconds (None = no L3 caching)
        cache_key_func: Optional function to generate custom cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            from .cache_manager import CacheManager
            
            # Get cache manager from server instance if available
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if cache_manager is None:
                # Try to get from global cache manager registry
                global_cache_manager = globals().get('_global_cache_manager', None)
                if global_cache_manager:
                    cache_manager = global_cache_manager
                    wrapper._cache_manager = cache_manager
                else:
                    # Fallback to creating new instance
                    cache_manager = CacheManager()
                    wrapper._cache_manager = cache_manager
            
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # Create a more specific cache key including function arguments
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                cache_key = f"{func.__name__}_{hash(str(sorted(bound_args.arguments.items())))}"
            
            # Try cache first - filter out cache-specific parameters from kwargs
            cache_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ('l1_ttl', 'l2_ttl', 'l3_ttl')}
            cached_result = cache_manager.get(namespace, cache_key, **cache_kwargs)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - execute function
            result = func(*args, **kwargs)
            
            # Store in cache - filter out cache-specific parameters from kwargs
            cache_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ('l1_ttl', 'l2_ttl', 'l3_ttl')}
            cache_manager.set(
                namespace, cache_key, result,
                l1_ttl=l1_ttl, l2_ttl=l2_ttl, l3_ttl=l3_ttl,
                **cache_kwargs
            )
            
            return result
        
        # Attach cache manager to function for reuse
        wrapper._cache_namespace = namespace
        wrapper._cache_manager = None
        
        return wrapper
    return decorator


def cache_invalidate(namespace: str, key: Optional[str] = None):
    """Decorator to invalidate cache after function execution.
    
    Args:
        namespace: Cache namespace to invalidate
        key: Specific key to invalidate (None = entire namespace)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function first
            result = func(*args, **kwargs)
            
            # Import here to avoid circular imports
            from .cache_manager import CacheManager
            
            # Get cache manager
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if cache_manager is None:
                cache_manager = CacheManager()
                wrapper._cache_manager = cache_manager
            
            # Invalidate cache - filter out cache-specific parameters from kwargs
            cache_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ('l1_ttl', 'l2_ttl', 'l3_ttl')}
            if key:
                invalidated = cache_manager.invalidate(namespace, key, **cache_kwargs)
            else:
                invalidated = cache_manager.invalidate(namespace, **cache_kwargs)
            
            logger.debug(f"Cache invalidation: {invalidated} entries removed from {namespace}")
            
            return result
        
        wrapper._cache_manager = None
        return wrapper
    return decorator


def set_cache_manager(func: Callable, cache_manager: Any) -> None:
    """Set cache manager instance on a cached function."""
    try:
        if hasattr(func, '_cache_manager'):
            func._cache_manager = cache_manager
    except (AttributeError, TypeError):
        # Silently skip if function doesn't support setting attributes
        # This handles bound methods and other non-settable function objects
        logger.debug(f"Cannot set cache manager on {func.__name__} - not a decorated function")
        pass
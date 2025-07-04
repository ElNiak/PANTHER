"""Multi-tier cache manager with L1 (memory), L2 (Redis), L3 (persistent) layers."""

import hashlib
import json
import os
import time
import logging
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import lru_cache

from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class CacheManager:
    """Multi-tier caching system for ATLAS MCP operations."""
    
    def __init__(self, 
                 l1_max_size: int = 128,
                 l2_default_ttl: int = 3600,  # 1 hour
                 l3_default_ttl: int = 86400,  # 1 day
                 l3_cache_dir: Optional[str] = None):
        """Initialize multi-tier cache manager.
        
        Args:
            l1_max_size: Maximum entries in L1 (memory) cache
            l2_default_ttl: Default TTL for L2 (Redis) cache in seconds
            l3_default_ttl: Default TTL for L3 (file) cache in seconds
            l3_cache_dir: Directory for L3 persistent cache
        """
        # L1 Cache (In-Memory) - fastest access
        self.l1_cache: Dict[str, Dict[str, Any]] = {}
        self.l1_max_size = l1_max_size
        self.l1_access_times: Dict[str, float] = {}
        
        # L2 Cache (Redis) - fast networked cache
        self.l2_client = RedisClient()
        self.l2_default_ttl = l2_default_ttl
        
        # L3 Cache (Persistent Files) - large stable cache
        if l3_cache_dir:
            self.l3_cache_dir = l3_cache_dir
        else:
            # Use Atlas home cache directory
            from atlas_commands.config.atlas_home import get_cache_dir
            self.l3_cache_dir = str(get_cache_dir())
        self.l3_default_ttl = l3_default_ttl
        os.makedirs(self.l3_cache_dir, exist_ok=True)
        
        # Cache statistics
        self.stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0, 
            'l3_hits': 0, 'l3_misses': 0,
            'total_gets': 0, 'total_sets': 0
        }
    
    def _generate_cache_key(self, namespace: str, key: str, **kwargs) -> str:
        """Generate hierarchical cache key."""
        key_parts = [namespace, key]
        
        # Add sorted kwargs as key parts  
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(hashlib.md5(
                json.dumps(sorted_kwargs, sort_keys=True).encode()
            ).hexdigest()[:8])
        
        return ':'.join(key_parts)
    
    def _evict_l1_lru(self) -> None:
        """Evict least recently used item from L1 cache."""
        if len(self.l1_cache) < self.l1_max_size:
            return
            
        # Find least recently used key
        lru_key = min(self.l1_access_times.items(), key=lambda x: x[1])[0]
        del self.l1_cache[lru_key]
        del self.l1_access_times[lru_key]
    
    def _is_l3_expired(self, filepath: str, ttl: int) -> bool:
        """Check if L3 cache file is expired."""
        if not os.path.exists(filepath):
            return True
        
        file_age = time.time() - os.path.getmtime(filepath)
        return file_age > ttl
    
    def get(self, namespace: str, key: str, **cache_kwargs) -> Optional[Any]:
        """Get value from multi-tier cache (L1 -> L2 -> L3)."""
        cache_key = self._generate_cache_key(namespace, key, **cache_kwargs)
        self.stats['total_gets'] += 1
        
        # Try L1 Cache first
        if cache_key in self.l1_cache:
            entry = self.l1_cache[cache_key]
            if time.time() < entry['expires_at']:
                self.l1_access_times[cache_key] = time.time()
                self.stats['l1_hits'] += 1
                logger.debug(f"L1 cache hit for {cache_key}")
                return entry['value']
            else:
                # Expired, remove from L1
                del self.l1_cache[cache_key]
                del self.l1_access_times[cache_key]
        
        self.stats['l1_misses'] += 1
        
        # Try L2 Cache (Redis)
        l2_value = self.l2_client.get(f"atlas:{cache_key}")
        if l2_value is not None:
            # Promote to L1
            self._set_l1(cache_key, l2_value, 300)  # 5 min in L1
            self.stats['l2_hits'] += 1
            logger.debug(f"L2 cache hit for {cache_key}")
            return l2_value
        
        self.stats['l2_misses'] += 1
        
        # Try L3 Cache (Files)
        l3_filepath = os.path.join(self.l3_cache_dir, f"{cache_key}.json")
        if not self._is_l3_expired(l3_filepath, self.l3_default_ttl):
            try:
                with open(l3_filepath, 'r') as f:
                    l3_value = json.load(f)
                
                # Promote to L2 and L1
                self.l2_client.set(f"atlas:{cache_key}", l3_value, self.l2_default_ttl)
                self._set_l1(cache_key, l3_value, 300)
                self.stats['l3_hits'] += 1
                logger.debug(f"L3 cache hit for {cache_key}")
                return l3_value
                
            except Exception as e:
                logger.warning(f"L3 cache read error for {cache_key}: {e}")
        
        self.stats['l3_misses'] += 1
        return None
    
    def _set_l1(self, cache_key: str, value: Any, ttl: int) -> None:
        """Set value in L1 cache with TTL."""
        self._evict_l1_lru()
        self.l1_cache[cache_key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
        self.l1_access_times[cache_key] = time.time()
    
    def set(self, namespace: str, key: str, value: Any, 
            l1_ttl: int = 300, l2_ttl: Optional[int] = None, l3_ttl: Optional[int] = None,
            **cache_kwargs) -> None:
        """Set value in all cache tiers."""
        cache_key = self._generate_cache_key(namespace, key, **cache_kwargs)
        self.stats['total_sets'] += 1
        
        # Set in L1 (memory)
        self._set_l1(cache_key, value, l1_ttl)
        
        # Set in L2 (Redis) 
        if self.l2_client.enabled:
            l2_ttl_actual = l2_ttl or self.l2_default_ttl
            self.l2_client.set(f"atlas:{cache_key}", value, l2_ttl_actual)
        
        # Set in L3 (files) for stable/large data
        if l3_ttl is not None:
            l3_filepath = os.path.join(self.l3_cache_dir, f"{cache_key}.json")
            try:
                with open(l3_filepath, 'w') as f:
                    json.dump(value, f, default=str)
                logger.debug(f"Stored in L3 cache: {cache_key}")
            except Exception as e:
                logger.warning(f"L3 cache write error for {cache_key}: {e}")
    
    def invalidate(self, namespace: str, key: str = None, **cache_kwargs) -> int:
        """Invalidate cache entries by namespace or specific key."""
        if key:
            # Invalidate specific key
            cache_key = self._generate_cache_key(namespace, key, **cache_kwargs)
            count = 0
            
            # Remove from L1
            if cache_key in self.l1_cache:
                del self.l1_cache[cache_key]
                del self.l1_access_times[cache_key]
                count += 1
            
            # Remove from L2
            if self.l2_client.delete(f"atlas:{cache_key}"):
                count += 1
            
            # Remove from L3
            l3_filepath = os.path.join(self.l3_cache_dir, f"{cache_key}.json")
            if os.path.exists(l3_filepath):
                os.remove(l3_filepath)
                count += 1
                
            return count
        else:
            # Invalidate entire namespace
            pattern = f"{namespace}:"
            count = 0
            
            # Remove from L1
            l1_keys_to_remove = [k for k in self.l1_cache.keys() if k.startswith(pattern)]
            for k in l1_keys_to_remove:
                del self.l1_cache[k]
                del self.l1_access_times[k]
                count += 1
            
            # Remove from L2
            count += self.l2_client.delete_pattern(f"atlas:{pattern}*")
            
            # Remove from L3
            for filename in os.listdir(self.l3_cache_dir):
                if filename.startswith(pattern) and filename.endswith('.json'):
                    os.remove(os.path.join(self.l3_cache_dir, filename))
                    count += 1
            
            return count
    
    def warm_cache(self, namespace: str, key: str, warm_func: Callable, 
                   *warm_args, **warm_kwargs) -> Any:
        """Warm cache by calling function if cache miss."""
        value = self.get(namespace, key, **warm_kwargs)
        if value is not None:
            return value
        
        # Cache miss - compute and store
        logger.info(f"Cache warming for {namespace}:{key}")
        computed_value = warm_func(*warm_args, **warm_kwargs)
        
        # Store in cache with smart TTL based on namespace
        if namespace == "task":
            self.set(namespace, key, computed_value, l1_ttl=300, l2_ttl=1800, l3_ttl=3600, **warm_kwargs)
        elif namespace == "memory":
            self.set(namespace, key, computed_value, l1_ttl=600, l2_ttl=3600, l3_ttl=7200, **warm_kwargs)
        elif namespace == "codacy":
            self.set(namespace, key, computed_value, l1_ttl=900, l2_ttl=7200, l3_ttl=14400, **warm_kwargs)
        else:
            self.set(namespace, key, computed_value, **warm_kwargs)
        
        return computed_value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_hits = self.stats['l1_hits'] + self.stats['l2_hits'] + self.stats['l3_hits']
        total_misses = self.stats['l1_misses'] + self.stats['l2_misses'] + self.stats['l3_misses']
        
        hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        
        return {
            **self.stats,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'hit_rate': round(hit_rate, 3),
            'l1_size': len(self.l1_cache),
            'l2_enabled': self.l2_client.enabled,
            'l3_cache_dir': self.l3_cache_dir
        }
    
    def clear_all(self) -> Dict[str, int]:
        """Clear all cache tiers."""
        # Clear L1
        l1_count = len(self.l1_cache)
        self.l1_cache.clear()
        self.l1_access_times.clear()
        
        # Clear L2
        l2_success = self.l2_client.flushdb() if self.l2_client.enabled else False
        
        # Clear L3
        l3_count = 0
        for filename in os.listdir(self.l3_cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.l3_cache_dir, filename))
                l3_count += 1
        
        return {
            'l1_cleared': l1_count,
            'l2_cleared': 1 if l2_success else 0,
            'l3_cleared': l3_count
        }
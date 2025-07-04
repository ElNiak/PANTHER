"""Redis client configuration and connection management."""

import os
import json
import logging
from typing import Any, Optional, Union
from datetime import timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with configuration management and fallback."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.enabled = False
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Redis client with environment configuration."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - caching disabled for L2 tier")
            return
            
        try:
            # Get Redis configuration from environment
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', '6379'))
            redis_db = int(os.environ.get('REDIS_DB', '0'))
            redis_password = os.environ.get('REDIS_PASSWORD')
            
            # Try to connect
            if redis_url.startswith('redis://'):
                self.client = redis.from_url(redis_url)
            else:
                self.client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
            
            # Test connection
            self.client.ping()
            self.enabled = True
            logger.info(f"Redis client initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}")
            self.client = None
            self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with JSON deserialization."""
        if not self.enabled or not self.client:
            return None
            
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set value in Redis with JSON serialization."""
        if not self.enabled or not self.client:
            return False
            
        try:
            serialized_value = json.dumps(value, default=str)
            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                return self.client.setex(key, ttl, serialized_value)
            else:
                return self.client.set(key, serialized_value)
        except Exception as e:
            logger.warning(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.enabled or not self.client:
            return False
            
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.warning(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.enabled or not self.client:
            return 0
            
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.enabled or not self.client:
            return False
            
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def flushdb(self) -> bool:
        """Flush current database (use with caution)."""
        if not self.enabled or not self.client:
            return False
            
        try:
            return self.client.flushdb()
        except Exception as e:
            logger.warning(f"Redis FLUSHDB error: {e}")
            return False
    
    def info(self) -> dict:
        """Get Redis server info."""
        if not self.enabled or not self.client:
            return {"status": "disabled", "reason": "Redis not available"}
            
        try:
            info = self.client.info()
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed")
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
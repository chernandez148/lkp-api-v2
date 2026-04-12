# app/utils/cache.py
import os
import json
import logging
from typing import Any, Optional, List
from dotenv import load_dotenv
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

load_dotenv()
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")  # keeping your var name for compatibility
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_USE_SSL = os.getenv("REDIS_USE_SSL", "false").lower() == "true"

# Create connection pool for better performance
pool_config = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": 0,
    "decode_responses": True,
    "socket_connect_timeout": 5,
    "socket_timeout": 5,
    "socket_keepalive": True,
    "health_check_interval": 30,
    "retry_on_timeout": True,
    "max_connections": 50,
}

if REDIS_PASSWORD:
    pool_config["password"] = REDIS_PASSWORD

if REDIS_USE_SSL:
    # This tells the pool to use the SSL Connection class
    from redis.asyncio import SSLConnection
    pool_config["connection_class"] = SSLConnection
    if os.getenv("ENVIRONMENT") == "development":
        pool_config["ssl_cert_reqs"] = None
    
pool = ConnectionPool(**pool_config)
redis = Redis(connection_pool=pool)


async def invalidate_cache(pattern: str) -> int:
    """
    Delete all keys in Redis that match the given pattern.
    
    Args:
        pattern: Redis pattern (e.g., "products:*" for all product keys)
        
    Returns:
        Number of keys deleted
        
    Warning:
        KEYS command can be slow on large databases. Consider using SCAN
        for production environments with many keys.
    """
    try:
        # Using SCAN is more production-friendly than KEYS
        deleted_count = 0
        cursor = 0
        
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
                deleted_count += len(keys)
            
            if cursor == 0:
                break
        
        if deleted_count > 0:
            logger.info(f"Invalidated {deleted_count} cache keys for pattern '{pattern}'")
        
        return deleted_count
        
    except RedisConnectionError as e:
        logger.error(f"Redis connection error while invalidating pattern '{pattern}': {e}")
        return 0
    except Exception as e:
        logger.error(f"Failed to invalidate cache for pattern '{pattern}': {e}")
        return 0


async def invalidate_cache_keys(keys: List[str]) -> int:
    """
    Delete specific cache keys.
    
    Args:
        keys: List of exact keys to delete
        
    Returns:
        Number of keys deleted
    """
    try:
        if not keys:
            return 0
            
        deleted = await redis.delete(*keys)
        logger.info(f"Invalidated {deleted} specific cache keys")
        return deleted
        
    except Exception as e:
        logger.error(f"Failed to invalidate specific keys: {e}")
        return 0


async def get_cached(key: str) -> Optional[Any]:
    """
    Retrieve cached data by key.
    
    Args:
        key: Cache key
        
    Returns:
        Cached data if found and valid, None otherwise
    """
    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
        return None
        
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in cache for key '{key}': {e}")
        # Delete corrupted cache entry
        await redis.delete(key)
        return None
        
    except RedisConnectionError as e:
        logger.warning(f"Redis connection error for key '{key}': {e}")
        return None
        
    except Exception as e:
        logger.warning(f"Cache get failed for key '{key}': {e}")
        return None


async def set_cached(key: str, value: Any, ttl: int = 60) -> bool:
    """
    Store data in cache with TTL.
    
    Args:
        key: Cache key
        value: Data to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: 60)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        serialized = json.dumps(value, default=str)
        await redis.set(key, serialized, ex=ttl)
        return True
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize value for key '{key}': {e}")
        return False
        
    except RedisConnectionError as e:
        logger.warning(f"Redis connection error while setting key '{key}': {e}")
        return False
        
    except Exception as e:
        logger.warning(f"Cache set failed for key '{key}': {e}")
        return False


async def exists_cached(key: str) -> bool:
    """Check if a key exists in cache."""
    try:
        return await redis.exists(key) > 0
    except Exception as e:
        logger.warning(f"Cache exists check failed for key '{key}': {e}")
        return False


async def get_ttl(key: str) -> int:
    """
    Get remaining TTL for a key.
    
    Returns:
        Remaining seconds, -1 if no TTL, -2 if key doesn't exist
    """
    try:
        return await redis.ttl(key)
    except Exception as e:
        logger.warning(f"Failed to get TTL for key '{key}': {e}")
        return -2


async def extend_ttl(key: str, additional_seconds: int) -> bool:
    """Extend the TTL of an existing key."""
    try:
        current_ttl = await redis.ttl(key)
        if current_ttl > 0:
            await redis.expire(key, current_ttl + additional_seconds)
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to extend TTL for key '{key}': {e}")
        return False


async def get_many_cached(keys: List[str]) -> dict:
    """
    Retrieve multiple cached values at once.
    
    Args:
        keys: List of cache keys
        
    Returns:
        Dictionary mapping keys to their values (only existing keys)
    """
    try:
        if not keys:
            return {}
        
        values = await redis.mget(keys)
        result = {}
        
        for key, value in zip(keys, values):
            if value:
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON for key '{key}'")
                    
        return result
        
    except Exception as e:
        logger.warning(f"Cache mget failed: {e}")
        return {}


async def set_many_cached(items: dict, ttl: int = 60) -> int:
    """
    Set multiple cache values at once.
    
    Args:
        items: Dictionary of key-value pairs
        ttl: Time to live in seconds
        
    Returns:
        Number of successfully set items
    """
    try:
        if not items:
            return 0
        
        pipe = redis.pipeline()
        count = 0
        
        for key, value in items.items():
            try:
                serialized = json.dumps(value, default=str)
                pipe.set(key, serialized, ex=ttl)
                count += 1
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize value for key '{key}': {e}")
        
        await pipe.execute()
        return count
        
    except Exception as e:
        logger.warning(f"Cache mset failed: {e}")
        return 0


async def ping_redis() -> bool:
    """Health check for Redis connection."""
    try:
        await redis.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


async def close_redis():
    """Close Redis connection pool gracefully."""
    try:
        await redis.close()
        await pool.disconnect()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")

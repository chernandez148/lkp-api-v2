# app/utils/cache.py
import json
import logging
from redis.asyncio import Redis, ConnectionPool

logger = logging.getLogger(__name__)

# Create connection pool for better performance
pool = ConnectionPool(host="127.0.0.1", port=6379, db=0, decode_responses=True)
redis = Redis(connection_pool=pool)

async def invalidate_cache(pattern: str):
    """
    Delete all keys in Redis that match the given pattern.
    Example: pattern="products:*" will delete all product-related cache.
    """
    try:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys for pattern '{pattern}'")
    except Exception as e:
        logger.error(f"Failed to invalidate cache for pattern '{pattern}': {e}")


async def get_cached(key: str):
    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning(f"Cache get failed for key '{key}': {e}")
        return None

async def set_cached(key: str, value, ttl: int = 60):
    try:
        await redis.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.warning(f"Cache set failed for key '{key}': {e}")
        # Don't raise - let the app continue without caching
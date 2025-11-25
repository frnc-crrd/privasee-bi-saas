"""
Caching utilities and decorators for Flask-Caching.

This module provides caching helpers for:
- Response caching
- Query result caching
- User session caching
- Analytics data caching
"""

from typing import Optional, Callable, Any
from functools import wraps
from flask import request
from flask_caching import Cache


# Cache instance (initialized in app factory)
cache = Cache()


def cache_key_prefix() -> str:
    """
    Generate cache key prefix based on current request.

    Returns:
        Cache key prefix string

    Example:
        >>> # In a request context
        >>> prefix = cache_key_prefix()
        >>> # Returns: "view//api/v1/users?page=1&limit=10"
    """
    return request.url


def cache_with_user_context(timeout: int = 300) -> Callable:
    """
    Cache decorator that includes user ID in cache key.

    Use this for user-specific data that should be cached separately
    per user.

    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)

    Returns:
        Decorator function

    Example:
        >>> @cache_with_user_context(timeout=600)
        >>> def get_user_dashboard_data(user_id: int):
        >>>     return expensive_query(user_id)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            # Extract user_id from kwargs or args
            user_id = kwargs.get('user_id') or (args[0] if args else 'anonymous')
            cache_key = f"{f.__name__}:user_{user_id}:{args}:{kwargs}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result

        return wrapper
    return decorator


def cache_query_result(timeout: int = 600) -> Callable:
    """
    Cache decorator for database query results.

    Use this for expensive queries that don't change frequently.

    Args:
        timeout: Cache timeout in seconds (default: 10 minutes)

    Returns:
        Decorator function

    Example:
        >>> @cache_query_result(timeout=1800)
        >>> def get_sales_summary(start_date: str, end_date: str):
        >>>     return db.session.execute(expensive_query).fetchall()
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            cache_key = f"query:{f.__name__}:{args}:{kwargs}"

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result

        return wrapper
    return decorator


def cache_analytics_data(timeout: int = 3600) -> Callable:
    """
    Cache decorator specifically for analytics/BI queries.

    Analytics data typically changes less frequently and can be
    cached for longer periods.

    Args:
        timeout: Cache timeout in seconds (default: 1 hour)

    Returns:
        Decorator function

    Example:
        >>> @cache_analytics_data(timeout=7200)
        >>> def get_monthly_revenue_trend():
        >>>     return analytics_engine.query(...)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            cache_key = f"analytics:{f.__name__}:{args}:{kwargs}"

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result

        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching a pattern.

    Args:
        pattern: Pattern to match (e.g., "user_*", "analytics:*")

    Returns:
        Number of keys deleted

    Example:
        >>> # Invalidate all user-related caches
        >>> invalidate_cache_pattern("user_*")
        >>> # Invalidate specific user's caches
        >>> invalidate_cache_pattern(f"*:user_{user_id}:*")
    """
    # Note: This requires Redis backend
    # For simple cache, use cache.clear() to clear all
    try:
        # If using Redis backend
        if hasattr(cache.cache, '_client'):
            redis_client = cache.cache._client
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return 0
        else:
            # Fallback: clear entire cache
            cache.clear()
            return -1  # Unknown count
    except Exception:
        # If pattern matching not supported, clear all
        cache.clear()
        return -1


def invalidate_user_cache(user_id: int) -> None:
    """
    Invalidate all cache entries for a specific user.

    Args:
        user_id: User ID whose cache should be invalidated

    Example:
        >>> # After user updates their profile
        >>> invalidate_user_cache(user_id=123)
    """
    invalidate_cache_pattern(f"*:user_{user_id}:*")


def invalidate_analytics_cache() -> None:
    """
    Invalidate all analytics cache entries.

    Use this after ETL pipeline runs or data updates.

    Example:
        >>> # After running ETL pipeline
        >>> invalidate_analytics_cache()
    """
    invalidate_cache_pattern("analytics:*")


class CacheConfig:
    """
    Cache configuration constants.

    These can be overridden in config.py based on environment.
    """

    # Cache type: 'simple', 'redis', 'memcached'
    CACHE_TYPE = 'simple'

    # Redis configuration (if using Redis)
    CACHE_REDIS_URL = 'redis://localhost:6379/0'

    # Default cache timeout (5 minutes)
    CACHE_DEFAULT_TIMEOUT = 300

    # Cache key prefix (to avoid collisions)
    CACHE_KEY_PREFIX = 'privasee_'

    # Timeout configurations by use case
    TIMEOUTS = {
        'user_session': 3600,      # 1 hour
        'user_data': 600,          # 10 minutes
        'analytics': 3600,         # 1 hour
        'query_result': 600,       # 10 minutes
        'api_response': 300,       # 5 minutes
        'static_data': 86400,      # 24 hours
    }

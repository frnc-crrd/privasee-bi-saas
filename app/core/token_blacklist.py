"""
Token blacklist management for logout and revocation.

This module provides an in-memory token blacklist for development.
For production, use Redis or database-backed storage.
"""

from datetime import datetime, timedelta, timezone
from typing import Set, Dict
from threading import Lock


class TokenBlacklist:
    """
    In-memory token blacklist for development.

    For production use, replace with Redis-backed implementation:
    - Use Redis SET with TTL matching token expiry
    - Key pattern: "blacklist:token:{jti}"
    - TTL: Token expiry duration
    """

    def __init__(self) -> None:
        """Initialize in-memory blacklist storage."""
        self._blacklisted_tokens: Dict[str, datetime] = {}
        self._lock = Lock()

    def add_token(self, jti: str, expires_at: datetime) -> None:
        """
        Add token to blacklist.

        Args:
            jti: JWT ID to blacklist
            expires_at: When token expires (for cleanup)

        Example:
            >>> blacklist = TokenBlacklist()
            >>> expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            >>> blacklist.add_token("abc123", expiry)
        """
        with self._lock:
            self._blacklisted_tokens[jti] = expires_at
            self._cleanup_expired_tokens()

    def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted, False otherwise

        Example:
            >>> blacklist.is_token_blacklisted("abc123")
            True
        """
        with self._lock:
            self._cleanup_expired_tokens()
            return jti in self._blacklisted_tokens

    def remove_token(self, jti: str) -> bool:
        """
        Remove token from blacklist (for testing/admin purposes).

        Args:
            jti: JWT ID to remove

        Returns:
            True if token was removed, False if not found
        """
        with self._lock:
            if jti in self._blacklisted_tokens:
                del self._blacklisted_tokens[jti]
                return True
            return False

    def _cleanup_expired_tokens(self) -> None:
        """
        Remove expired tokens from blacklist.

        This method is called automatically during add/check operations
        to prevent memory bloat.
        """
        now = datetime.now(timezone.utc)
        expired_jtis = [
            jti for jti, expires_at in self._blacklisted_tokens.items()
            if expires_at <= now
        ]
        for jti in expired_jtis:
            del self._blacklisted_tokens[jti]

    def get_blacklist_size(self) -> int:
        """
        Get current number of blacklisted tokens.

        Returns:
            Number of tokens in blacklist

        Example:
            >>> size = blacklist.get_blacklist_size()
        """
        with self._lock:
            self._cleanup_expired_tokens()
            return len(self._blacklisted_tokens)

    def clear_all(self) -> None:
        """
        Clear all tokens from blacklist (for testing purposes).

        Warning:
            This should only be used in testing environments.
        """
        with self._lock:
            self._blacklisted_tokens.clear()


class RedisTokenBlacklist:
    """
    Redis-backed token blacklist for production use.

    This is a placeholder implementation. To use:
    1. Install redis: pip install redis
    2. Configure Redis connection in config.py
    3. Replace TokenBlacklist with this class in extensions.py
    """

    def __init__(self, redis_client=None) -> None:
        """
        Initialize Redis blacklist.

        Args:
            redis_client: Redis client instance (optional, will use default if None)
        """
        self.redis_client = redis_client
        # TODO: Initialize redis_client from app config
        # from redis import Redis
        # self.redis_client = redis_client or Redis.from_url(current_app.config['REDIS_URL'])

    def add_token(self, jti: str, expires_at: datetime) -> None:
        """
        Add token to Redis blacklist with TTL.

        Args:
            jti: JWT ID to blacklist
            expires_at: When token expires
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured")

        # Calculate TTL in seconds
        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            key = f"blacklist:token:{jti}"
            self.redis_client.setex(key, ttl, "1")

    def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted in Redis.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured")

        key = f"blacklist:token:{jti}"
        return self.redis_client.exists(key) > 0

    def remove_token(self, jti: str) -> bool:
        """
        Remove token from Redis blacklist.

        Args:
            jti: JWT ID to remove

        Returns:
            True if token was removed, False if not found
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured")

        key = f"blacklist:token:{jti}"
        return self.redis_client.delete(key) > 0


# Global instance (initialized in app factory)
token_blacklist = TokenBlacklist()

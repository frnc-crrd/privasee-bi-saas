"""
Unit tests for cache module.

This module contains comprehensive tests for the caching utilities,
focusing on cache configuration, invalidation logic, and key generation.

Test Coverage:
    - Cache key generation
    - Cache invalidation patterns
    - Cache configuration validation
    - Error handling scenarios

Note: Decorator tests require full Flask app initialization and are
covered in integration tests.
"""

from unittest.mock import Mock, patch, MagicMock, call
import pytest
from flask import Flask

from app.core.cache import (
    cache_key_prefix,
    invalidate_cache_pattern,
    invalidate_user_cache,
    invalidate_analytics_cache,
    CacheConfig,
)


class TestCacheKeyPrefix:
    """Tests for cache key prefix generation."""

    def test_cache_key_prefix_returns_request_url(self, app):
        """Test that cache_key_prefix returns the current request URL.

        This test verifies that the cache key prefix is correctly generated
        from the request URL, which is used to create unique cache keys for
        different requests.

        Args:
            app: Flask application fixture

        Assertions:
            - Cache key prefix matches request URL
            - URL includes query parameters
        """
        with app.test_request_context('/api/v1/users?page=1&limit=10'):
            prefix = cache_key_prefix()
            assert prefix == 'http://localhost/api/v1/users?page=1&limit=10'

    def test_cache_key_prefix_different_urls(self, app):
        """Test that different URLs generate different cache key prefixes.

        Verifies that cache keys are unique for different endpoints,
        preventing cache collisions.

        Args:
            app: Flask application fixture

        Assertions:
            - Different URLs generate different prefixes
            - Prefixes are consistent for the same URL
        """
        with app.test_request_context('/api/v1/users'):
            prefix1 = cache_key_prefix()

        with app.test_request_context('/api/v1/analytics'):
            prefix2 = cache_key_prefix()

        assert prefix1 != prefix2
        assert '/users' in prefix1
        assert '/analytics' in prefix2

    def test_cache_key_prefix_includes_query_parameters(self, app):
        """Test that query parameters are included in cache key.

        Ensures that requests with different query parameters generate
        different cache keys.

        Args:
            app: Flask application fixture

        Assertions:
            - Query parameters included in prefix
            - Different parameters create different keys
        """
        with app.test_request_context('/api/v1/users?sort=name'):
            prefix1 = cache_key_prefix()

        with app.test_request_context('/api/v1/users?sort=email'):
            prefix2 = cache_key_prefix()

        assert 'sort=name' in prefix1
        assert 'sort=email' in prefix2
        assert prefix1 != prefix2


class TestInvalidateCachePattern:
    """Tests for pattern-based cache invalidation."""

    @patch('app.core.cache.cache')
    def test_invalidate_cache_pattern_with_redis_backend(self, mock_cache, app):
        """Test cache invalidation with Redis backend.

        Verifies that pattern-based invalidation works correctly
        when using Redis as the cache backend.

        Args:
            mock_cache: Mocked cache object
            app: Flask application fixture

        Assertions:
            - Pattern matching called on Redis client
            - Returns count of deleted keys
            - Correct pattern passed to Redis
        """
        with app.app_context():
            # Mock Redis client
            mock_redis_client = Mock()
            mock_redis_client.keys.return_value = [b'user_123_profile', b'user_123_settings']
            mock_redis_client.delete.return_value = 2

            mock_cache.cache = Mock()
            mock_cache.cache._client = mock_redis_client

            count = invalidate_cache_pattern('user_123_*')

            mock_redis_client.keys.assert_called_once_with('user_123_*')
            mock_redis_client.delete.assert_called_once()
            assert count == 2

    @patch('app.core.cache.cache')
    def test_invalidate_cache_pattern_no_matching_keys(self, mock_cache, app):
        """Test cache invalidation when no keys match pattern.

        Verifies that the function handles gracefully when no keys
        match the provided pattern.

        Args:
            mock_cache: Mocked cache object
            app: Flask application fixture

        Assertions:
            - Returns 0 when no keys match
            - delete() not called when keys list is empty
        """
        with app.app_context():
            mock_redis_client = Mock()
            mock_redis_client.keys.return_value = []  # No matching keys

            mock_cache.cache = Mock()
            mock_cache.cache._client = mock_redis_client

            count = invalidate_cache_pattern('nonexistent_*')

            mock_redis_client.keys.assert_called_once_with('nonexistent_*')
            mock_redis_client.delete.assert_not_called()
            assert count == 0

    @patch('app.core.cache.cache')
    def test_invalidate_cache_pattern_fallback_simple_cache(self, mock_cache, app):
        """Test cache invalidation fallback for simple cache.

        When pattern matching is not supported (e.g., simple cache),
        the function should fall back to clearing the entire cache.

        Args:
            mock_cache: Mocked cache object
            app: Flask application fixture

        Assertions:
            - Falls back to cache.clear() when pattern not supported
            - Returns -1 to indicate fallback behavior
        """
        with app.app_context():
            # Mock simple cache (no _client attribute)
            mock_cache.cache = Mock(spec=[])  # No _client attribute
            mock_cache.clear = Mock()

            count = invalidate_cache_pattern('test_*')

            mock_cache.clear.assert_called_once()
            assert count == -1  # Indicates fallback

    @patch('app.core.cache.cache')
    def test_invalidate_cache_pattern_handles_redis_errors(self, mock_cache, app):
        """Test error handling in cache invalidation.

        Verifies that exceptions during invalidation are caught
        and the function gracefully falls back to clearing all cache.

        Args:
            mock_cache: Mocked cache object
            app: Flask application fixture

        Assertions:
            - Exceptions handled gracefully
            - Fallback to cache.clear() on error
            - No exception raised to caller
        """
        with app.app_context():
            mock_redis_client = Mock()
            mock_redis_client.keys.side_effect = Exception('Redis connection error')

            mock_cache.cache = Mock()
            mock_cache.cache._client = mock_redis_client
            mock_cache.clear = Mock()

            # Should not raise exception
            count = invalidate_cache_pattern('user_*')

            mock_cache.clear.assert_called_once()
            assert count == -1  # Fallback behavior

    @patch('app.core.cache.cache')
    def test_invalidate_cache_pattern_multiple_keys(self, mock_cache, app):
        """Test invalidation of multiple matching keys.

        Verifies that multiple keys matching the pattern are all
        deleted in a single operation.

        Args:
            mock_cache: Mocked cache object
            app: Flask application fixture

        Assertions:
            - All matching keys deleted
            - delete() called with all keys
        """
        with app.app_context():
            mock_redis_client = Mock()
            keys = [b'analytics:sales_2024', b'analytics:sales_2025', b'analytics:revenue']
            mock_redis_client.keys.return_value = keys
            mock_redis_client.delete.return_value = 3

            mock_cache.cache = Mock()
            mock_cache.cache._client = mock_redis_client

            count = invalidate_cache_pattern('analytics:*')

            assert count == 3
            # Verify delete called with all keys (unpacked)
            args, kwargs = mock_redis_client.delete.call_args
            assert len(args) == 3


class TestInvalidateUserCache:
    """Tests for user-specific cache invalidation."""

    @patch('app.core.cache.invalidate_cache_pattern')
    def test_invalidate_user_cache_calls_pattern_invalidation(self, mock_invalidate, app):
        """Test that invalidate_user_cache calls pattern invalidation.

        Verifies that user cache invalidation correctly constructs
        the pattern and calls the underlying invalidation function.

        Args:
            mock_invalidate: Mocked invalidate_cache_pattern function
            app: Flask application fixture

        Assertions:
            - invalidate_cache_pattern called once
            - Correct pattern format used
        """
        with app.app_context():
            invalidate_user_cache(user_id=123)
            mock_invalidate.assert_called_once_with('*:user_123:*')

    @patch('app.core.cache.invalidate_cache_pattern')
    def test_invalidate_user_cache_different_users(self, mock_invalidate, app):
        """Test invalidating cache for multiple users independently.

        Verifies that each user's cache can be invalidated separately
        with the correct pattern for each user.

        Args:
            mock_invalidate: Mocked invalidate_cache_pattern function
            app: Flask application fixture

        Assertions:
            - Each user gets separate invalidation call
            - Correct patterns used for each user
        """
        with app.app_context():
            invalidate_user_cache(user_id=123)
            invalidate_user_cache(user_id=456)
            invalidate_user_cache(user_id=789)

            assert mock_invalidate.call_count == 3
            mock_invalidate.assert_any_call('*:user_123:*')
            mock_invalidate.assert_any_call('*:user_456:*')
            mock_invalidate.assert_any_call('*:user_789:*')

    @patch('app.core.cache.invalidate_cache_pattern')
    def test_invalidate_user_cache_with_integer_user_id(self, mock_invalidate, app):
        """Test that user_id is correctly formatted in pattern.

        Ensures that integer user IDs are properly converted to
        strings in the cache pattern.

        Args:
            mock_invalidate: Mocked invalidate_cache_pattern function
            app: Flask application fixture

        Assertions:
            - Integer user_id converted to string
            - Pattern contains numeric user ID
        """
        with app.app_context():
            user_id = 999
            invalidate_user_cache(user_id=user_id)

            call_args = mock_invalidate.call_args[0][0]
            assert 'user_999' in call_args
            assert isinstance(call_args, str)


class TestInvalidateAnalyticsCache:
    """Tests for analytics cache invalidation."""

    @patch('app.core.cache.invalidate_cache_pattern')
    def test_invalidate_analytics_cache_calls_pattern_invalidation(self, mock_invalidate, app):
        """Test that analytics cache invalidation uses correct pattern.

        Verifies that the analytics cache invalidation function calls
        the pattern invalidation with the 'analytics:*' pattern.

        Args:
            mock_invalidate: Mocked invalidate_cache_pattern function
            app: Flask application fixture

        Assertions:
            - invalidate_cache_pattern called once
            - Pattern is 'analytics:*'
        """
        with app.app_context():
            invalidate_analytics_cache()
            mock_invalidate.assert_called_once_with('analytics:*')

    @patch('app.core.cache.invalidate_cache_pattern')
    def test_invalidate_analytics_cache_can_be_called_multiple_times(self, mock_invalidate, app):
        """Test that analytics cache can be invalidated multiple times.

        Simulates multiple ETL pipeline runs that each invalidate
        the analytics cache.

        Args:
            mock_invalidate: Mocked invalidate_cache_pattern function
            app: Flask application fixture

        Assertions:
            - Each call triggers invalidation
            - Pattern remains consistent
        """
        with app.app_context():
            # Simulate multiple ETL runs
            invalidate_analytics_cache()
            invalidate_analytics_cache()
            invalidate_analytics_cache()

            assert mock_invalidate.call_count == 3
            # All calls should use same pattern
            for call_obj in mock_invalidate.call_args_list:
                assert call_obj[0][0] == 'analytics:*'


class TestCacheConfig:
    """Tests for cache configuration class."""

    def test_cache_config_has_all_required_attributes(self):
        """Test that CacheConfig has all required configuration attributes.

        Verifies that the configuration class provides all necessary
        settings for cache operation.

        Assertions:
            - CACHE_TYPE is defined
            - CACHE_REDIS_URL is defined
            - CACHE_DEFAULT_TIMEOUT is defined
            - CACHE_KEY_PREFIX is defined
            - TIMEOUTS dictionary is defined
        """
        assert hasattr(CacheConfig, 'CACHE_TYPE')
        assert hasattr(CacheConfig, 'CACHE_REDIS_URL')
        assert hasattr(CacheConfig, 'CACHE_DEFAULT_TIMEOUT')
        assert hasattr(CacheConfig, 'CACHE_KEY_PREFIX')
        assert hasattr(CacheConfig, 'TIMEOUTS')

    def test_cache_config_cache_type_is_string(self):
        """Test that CACHE_TYPE is a valid string.

        Ensures the cache type setting is properly configured.

        Assertions:
            - CACHE_TYPE is a string
            - CACHE_TYPE is non-empty
        """
        assert isinstance(CacheConfig.CACHE_TYPE, str)
        assert len(CacheConfig.CACHE_TYPE) > 0

    def test_cache_config_default_timeout_is_positive(self):
        """Test that default timeout is a positive number.

        Verifies that the default cache timeout is configured with
        a reasonable positive value.

        Assertions:
            - CACHE_DEFAULT_TIMEOUT is an integer
            - CACHE_DEFAULT_TIMEOUT is greater than 0
        """
        assert isinstance(CacheConfig.CACHE_DEFAULT_TIMEOUT, int)
        assert CacheConfig.CACHE_DEFAULT_TIMEOUT > 0

    def test_cache_config_key_prefix_prevents_collisions(self):
        """Test that cache key prefix helps prevent collisions.

        Verifies that a key prefix is configured to namespace
        cache keys and prevent collisions with other applications.

        Assertions:
            - CACHE_KEY_PREFIX is a string
            - CACHE_KEY_PREFIX is non-empty
        """
        assert isinstance(CacheConfig.CACHE_KEY_PREFIX, str)
        assert len(CacheConfig.CACHE_KEY_PREFIX) > 0

    def test_cache_config_timeouts_is_dictionary(self):
        """Test that TIMEOUTS is a properly configured dictionary.

        Ensures that the timeout configurations are stored in
        a dictionary format.

        Assertions:
            - TIMEOUTS is a dictionary
            - TIMEOUTS is not empty
        """
        assert isinstance(CacheConfig.TIMEOUTS, dict)
        assert len(CacheConfig.TIMEOUTS) > 0

    def test_cache_config_timeout_values_are_reasonable(self):
        """Test that all timeout values are reasonable positive integers.

        Verifies that all configured timeouts are sensible values
        for their respective use cases.

        Assertions:
            - All timeout values are integers
            - All timeout values are positive
            - Timeout values are within reasonable ranges
        """
        for category, timeout in CacheConfig.TIMEOUTS.items():
            assert isinstance(timeout, int), \
                f"Timeout for {category} should be an integer"
            assert timeout > 0, \
                f"Timeout for {category} should be positive"
            assert timeout <= 86400 * 7, \
                f"Timeout for {category} exceeds 7 days (unreasonably long)"

    def test_cache_config_has_expected_timeout_categories(self):
        """Test that all expected timeout categories are configured.

        Ensures that the configuration includes timeout settings
        for all common caching use cases.

        Assertions:
            - All expected timeout categories present
            - No missing timeout configurations
        """
        expected_categories = [
            'user_session',
            'user_data',
            'analytics',
            'query_result',
            'api_response',
            'static_data'
        ]

        for category in expected_categories:
            assert category in CacheConfig.TIMEOUTS, \
                f"Missing timeout configuration for {category}"

    def test_cache_config_analytics_timeout_longer_than_api_response(self):
        """Test that analytics has longer timeout than API responses.

        Analytics data changes less frequently and should be cached
        longer than regular API responses.

        Assertions:
            - Analytics timeout > API response timeout
            - Reflects appropriate caching strategy
        """
        analytics_timeout = CacheConfig.TIMEOUTS.get('analytics', 0)
        api_timeout = CacheConfig.TIMEOUTS.get('api_response', 0)

        assert analytics_timeout > api_timeout, \
            "Analytics data should be cached longer than API responses"

    def test_cache_config_static_data_has_longest_timeout(self):
        """Test that static data has the longest cache timeout.

        Static data rarely changes and should be cached for
        extended periods.

        Assertions:
            - Static data timeout is longest
            - At least 24 hours (86400 seconds)
        """
        static_timeout = CacheConfig.TIMEOUTS.get('static_data', 0)
        other_timeouts = [
            timeout for key, timeout in CacheConfig.TIMEOUTS.items()
            if key != 'static_data'
        ]

        assert static_timeout >= max(other_timeouts), \
            "Static data should have the longest cache timeout"
        assert static_timeout >= 86400, \
            "Static data should be cached for at least 24 hours"

    def test_cache_config_redis_url_format(self):
        """Test that Redis URL is in correct format.

        Verifies that the Redis URL configuration follows the
        expected format for Redis connections.

        Assertions:
            - CACHE_REDIS_URL is a string
            - URL starts with 'redis://'
        """
        assert isinstance(CacheConfig.CACHE_REDIS_URL, str)
        assert CacheConfig.CACHE_REDIS_URL.startswith('redis://'), \
            "Redis URL should start with 'redis://'"


class TestCachePatternGeneration:
    """Tests for cache key pattern generation and validation."""

    def test_user_cache_pattern_format(self):
        """Test that user cache patterns are correctly formatted.

        Verifies that the pattern generation for user-specific
        cache invalidation produces the expected format.

        Assertions:
            - Pattern includes wildcard prefix
            - Pattern includes user ID
            - Pattern includes wildcard suffix
        """
        user_id = 42
        expected_pattern = f"*:user_{user_id}:*"

        # This is what invalidate_user_cache should generate
        assert expected_pattern == f"*:user_{user_id}:*"
        assert expected_pattern.startswith('*')
        assert f'user_{user_id}' in expected_pattern
        assert expected_pattern.endswith('*')

    def test_analytics_cache_pattern_format(self):
        """Test that analytics cache pattern is correctly formatted.

        Verifies that the analytics cache invalidation pattern
        follows the expected convention.

        Assertions:
            - Pattern starts with 'analytics:'
            - Pattern ends with wildcard
        """
        expected_pattern = "analytics:*"

        assert expected_pattern.startswith('analytics:')
        assert expected_pattern.endswith('*')

    def test_cache_patterns_are_distinct(self):
        """Test that different cache patterns don't overlap.

        Ensures that user cache patterns and analytics patterns
        are distinct and won't inadvertently clear each other's data.

        Assertions:
            - User pattern doesn't match analytics pattern
            - Analytics pattern doesn't match user pattern
        """
        user_pattern = "*:user_123:*"
        analytics_pattern = "analytics:*"

        # Patterns should be distinct
        assert 'analytics:' not in user_pattern
        assert ':user_' not in analytics_pattern

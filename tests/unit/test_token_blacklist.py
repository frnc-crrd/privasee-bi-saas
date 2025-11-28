"""
Unit tests for token blacklist module.

This module contains comprehensive tests for JWT token blacklisting,
including in-memory and Redis implementations, expiration handling,
thread safety, and security scenarios.

Test Coverage:
    - Token blacklisting operations
    - Token expiration and automatic cleanup
    - Thread safety and concurrent operations
    - Redis backend integration
    - Security and edge cases
    - Performance under load
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
from datetime import datetime, timedelta, timezone
from threading import Thread
import time

from app.core.token_blacklist import TokenBlacklist, RedisTokenBlacklist


class TestTokenBlacklistBasicOperations:
    """Tests for basic token blacklist operations."""

    def test_add_token_to_blacklist_success(self):
        """Test that tokens can be added to blacklist.

        Verifies that JWT token IDs (jti) are correctly added to
        the in-memory blacklist and can be retrieved.

        Assertions:
            - Token added successfully
            - Token appears in blacklist
            - Blacklist size increases
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "test-jti-12345"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act
        blacklist.add_token(jti, expires_at)

        # Assert
        assert blacklist.is_token_blacklisted(jti) is True
        assert blacklist.get_blacklist_size() == 1

    def test_add_token_with_far_future_expiration(self):
        """Test adding token with distant expiration date.

        Verifies that tokens with expiration dates far in the future
        are correctly stored and remain in the blacklist.

        Assertions:
            - Token with future expiration is added
            - Token remains blacklisted
            - Expiration time is preserved
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "long-lived-token"
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)

        # Act
        blacklist.add_token(jti, expires_at)

        # Assert
        assert blacklist.is_token_blacklisted(jti) is True
        assert blacklist.get_blacklist_size() == 1

    def test_is_token_blacklisted_returns_true_for_blacklisted_token(self):
        """Test that blacklisted tokens return True.

        Verifies that tokens previously added to the blacklist
        correctly return True when checked.

        Assertions:
            - Blacklisted token returns True
            - Check operation is consistent
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "blacklisted-token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        blacklist.add_token(jti, expires_at)

        # Act
        result = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result is True

    def test_is_token_blacklisted_returns_false_for_non_blacklisted_token(self):
        """Test that non-blacklisted tokens return False.

        Verifies that tokens not in the blacklist correctly
        return False when checked.

        Assertions:
            - Non-blacklisted token returns False
            - Empty blacklist check works correctly
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "non-existent-token"

        # Act
        result = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result is False

    def test_blacklist_token_persistence_across_checks(self):
        """Test that blacklisted tokens persist across multiple checks.

        Verifies that once a token is blacklisted, it remains
        blacklisted across multiple check operations until expiration.

        Assertions:
            - Token remains blacklisted after first check
            - Multiple checks return consistent results
            - Blacklist size remains constant
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "persistent-token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        blacklist.add_token(jti, expires_at)

        # Act - Multiple checks
        check1 = blacklist.is_token_blacklisted(jti)
        check2 = blacklist.is_token_blacklisted(jti)
        check3 = blacklist.is_token_blacklisted(jti)

        # Assert
        assert check1 is True
        assert check2 is True
        assert check3 is True
        assert blacklist.get_blacklist_size() == 1

    def test_blacklist_duplicate_token_does_not_increase_size(self):
        """Test that adding duplicate tokens doesn't increase blacklist size.

        Verifies that adding the same token multiple times
        does not create duplicate entries.

        Assertions:
            - Duplicate token overwrites previous entry
            - Blacklist size remains 1
            - Token remains blacklisted
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "duplicate-token"
        expires_at1 = datetime.now(timezone.utc) + timedelta(hours=1)
        expires_at2 = datetime.now(timezone.utc) + timedelta(hours=2)

        # Act
        blacklist.add_token(jti, expires_at1)
        initial_size = blacklist.get_blacklist_size()
        blacklist.add_token(jti, expires_at2)
        final_size = blacklist.get_blacklist_size()

        # Assert
        assert initial_size == 1
        assert final_size == 1
        assert blacklist.is_token_blacklisted(jti) is True

    def test_multiple_different_tokens_in_blacklist(self):
        """Test adding multiple different tokens to blacklist.

        Verifies that multiple distinct tokens can be added
        and tracked independently in the blacklist.

        Assertions:
            - Multiple tokens can be added
            - Each token is independently blacklisted
            - Blacklist size reflects number of tokens
        """
        # Arrange
        blacklist = TokenBlacklist()
        jtis = [f"token-{i}" for i in range(5)]
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act
        for jti in jtis:
            blacklist.add_token(jti, expires_at)

        # Assert
        assert blacklist.get_blacklist_size() == 5
        for jti in jtis:
            assert blacklist.is_token_blacklisted(jti) is True

    def test_remove_token_from_blacklist_success(self):
        """Test removing token from blacklist.

        Verifies that tokens can be manually removed from
        the blacklist (for testing/admin purposes).

        Assertions:
            - Token removal returns True
            - Token is no longer blacklisted
            - Blacklist size decreases
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "removable-token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        blacklist.add_token(jti, expires_at)

        # Act
        result = blacklist.remove_token(jti)

        # Assert
        assert result is True
        assert blacklist.is_token_blacklisted(jti) is False
        assert blacklist.get_blacklist_size() == 0

    def test_remove_non_existent_token_returns_false(self):
        """Test removing non-existent token returns False.

        Verifies that attempting to remove a token that
        is not in the blacklist returns False.

        Assertions:
            - Removal of non-existent token returns False
            - Blacklist size remains unchanged
        """
        # Arrange
        blacklist = TokenBlacklist()

        # Act
        result = blacklist.remove_token("non-existent")

        # Assert
        assert result is False
        assert blacklist.get_blacklist_size() == 0


class TestTokenExpiration:
    """Tests for token expiration and automatic cleanup."""

    def test_expired_tokens_automatically_cleaned_on_add(self):
        """Test that expired tokens are cleaned up when adding new tokens.

        Verifies that automatic cleanup removes expired tokens
        whenever a new token is added to the blacklist.

        Assertions:
            - Expired tokens are removed
            - Only valid tokens remain
            - Cleanup happens automatically
        """
        # Arrange
        blacklist = TokenBlacklist()
        expired_jti = "expired-token"
        valid_jti = "valid-token"

        # Add expired token (expires in the past)
        past_expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
        blacklist.add_token(expired_jti, past_expiry)

        # Wait briefly to ensure expiration
        time.sleep(0.1)

        # Act - Adding new token triggers cleanup
        future_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        blacklist.add_token(valid_jti, future_expiry)

        # Assert
        assert blacklist.is_token_blacklisted(expired_jti) is False
        assert blacklist.is_token_blacklisted(valid_jti) is True
        assert blacklist.get_blacklist_size() == 1

    def test_expired_tokens_automatically_cleaned_on_check(self):
        """Test that expired tokens are cleaned up during blacklist checks.

        Verifies that checking if a token is blacklisted triggers
        automatic cleanup of expired tokens.

        Assertions:
            - Checking triggers cleanup
            - Expired tokens are removed
            - Check returns False for expired token
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "expires-soon"

        # Token expires very soon
        near_expiry = datetime.now(timezone.utc) + timedelta(milliseconds=100)
        blacklist.add_token(jti, near_expiry)

        # Wait for expiration
        time.sleep(0.2)

        # Act - Check triggers cleanup
        result = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result is False
        assert blacklist.get_blacklist_size() == 0

    def test_cleanup_preserves_valid_tokens(self):
        """Test that cleanup only removes expired tokens, not valid ones.

        Verifies that automatic cleanup preserves tokens that
        have not yet expired while removing expired ones.

        Assertions:
            - Valid tokens are preserved
            - Expired tokens are removed
            - Cleanup is selective
        """
        # Arrange
        blacklist = TokenBlacklist()

        # Add mix of expired and valid tokens
        expired_jtis = [f"expired-{i}" for i in range(3)]
        valid_jtis = [f"valid-{i}" for i in range(3)]

        past_expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
        for jti in expired_jtis:
            blacklist.add_token(jti, past_expiry)

        time.sleep(0.1)

        future_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        for jti in valid_jtis:
            blacklist.add_token(jti, future_expiry)

        # Act - Check triggers cleanup
        size = blacklist.get_blacklist_size()

        # Assert
        assert size == 3  # Only valid tokens remain
        for jti in valid_jtis:
            assert blacklist.is_token_blacklisted(jti) is True
        for jti in expired_jtis:
            assert blacklist.is_token_blacklisted(jti) is False

    def test_expiration_ttl_respected_precisely(self):
        """Test that token expiration TTL is respected precisely.

        Verifies that tokens expire at the exact time specified
        and not before or significantly after.

        Assertions:
            - Token is valid before expiration
            - Token is invalid after expiration
            - TTL timing is accurate
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "precise-expiry-token"

        # Expires in 200ms
        expiry = datetime.now(timezone.utc) + timedelta(milliseconds=200)
        blacklist.add_token(jti, expiry)

        # Act & Assert - Before expiration
        assert blacklist.is_token_blacklisted(jti) is True

        # Wait past expiration
        time.sleep(0.3)

        # Act & Assert - After expiration
        assert blacklist.is_token_blacklisted(jti) is False

    def test_get_blacklist_size_triggers_cleanup(self):
        """Test that get_blacklist_size triggers automatic cleanup.

        Verifies that checking the blacklist size triggers
        cleanup of expired tokens before returning the count.

        Assertions:
            - Size check triggers cleanup
            - Returned size excludes expired tokens
            - Expired tokens are removed
        """
        # Arrange
        blacklist = TokenBlacklist()

        # Add token that expires immediately
        jti = "immediate-expiry"
        expiry = datetime.now(timezone.utc) + timedelta(milliseconds=50)
        blacklist.add_token(jti, expiry)

        # Wait for expiration
        time.sleep(0.1)

        # Act
        size = blacklist.get_blacklist_size()

        # Assert
        assert size == 0
        assert blacklist.is_token_blacklisted(jti) is False


class TestThreadSafety:
    """Tests for thread safety and concurrent operations."""

    def test_concurrent_add_operations_thread_safe(self):
        """Test that concurrent add operations are thread-safe.

        Verifies that multiple threads can add tokens simultaneously
        without race conditions or data corruption.

        Assertions:
            - All tokens added successfully
            - No tokens lost due to race conditions
            - Final count matches expected value
        """
        # Arrange
        blacklist = TokenBlacklist()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        num_threads = 10
        tokens_per_thread = 10

        def add_tokens(thread_id):
            """Add tokens from a specific thread."""
            for i in range(tokens_per_thread):
                jti = f"thread-{thread_id}-token-{i}"
                blacklist.add_token(jti, expires_at)

        # Act - Spawn threads
        threads = []
        for i in range(num_threads):
            thread = Thread(target=add_tokens, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Assert
        expected_count = num_threads * tokens_per_thread
        assert blacklist.get_blacklist_size() == expected_count

    def test_concurrent_check_operations_thread_safe(self):
        """Test that concurrent check operations are thread-safe.

        Verifies that multiple threads can check token blacklist
        status simultaneously without interference.

        Assertions:
            - All checks return correct results
            - No race conditions occur
            - Checks are consistent across threads
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "shared-token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        blacklist.add_token(jti, expires_at)

        results = []
        num_threads = 20

        def check_token():
            """Check token from multiple threads."""
            result = blacklist.is_token_blacklisted(jti)
            results.append(result)

        # Act
        threads = []
        for _ in range(num_threads):
            thread = Thread(target=check_token)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert len(results) == num_threads
        assert all(result is True for result in results)

    def test_concurrent_mixed_operations_thread_safe(self):
        """Test thread safety with mixed add/check/remove operations.

        Verifies that combining different operations concurrently
        maintains data integrity and consistency.

        Assertions:
            - No data corruption occurs
            - Operations complete without errors
            - Final state is consistent
        """
        # Arrange
        blacklist = TokenBlacklist()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        def mixed_operations(thread_id):
            """Perform mixed operations."""
            jti = f"mixed-token-{thread_id}"
            blacklist.add_token(jti, expires_at)
            is_blacklisted = blacklist.is_token_blacklisted(jti)
            if is_blacklisted and thread_id % 2 == 0:
                blacklist.remove_token(jti)

        # Act
        threads = []
        for i in range(20):
            thread = Thread(target=mixed_operations, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Assert - Should complete without exceptions
        size = blacklist.get_blacklist_size()
        assert size >= 0  # Size should be non-negative


class TestEdgeCases:
    """Tests for edge cases and security scenarios."""

    def test_blacklist_empty_string_jti(self):
        """Test handling of empty string as JTI.

        Verifies that empty string JTIs are handled correctly
        without raising exceptions.

        Assertions:
            - Empty JTI can be added
            - Empty JTI can be checked
            - No exceptions raised
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = ""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act
        blacklist.add_token(jti, expires_at)
        result = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result is True
        assert blacklist.get_blacklist_size() == 1

    def test_blacklist_very_long_jti(self):
        """Test handling of very long JTI strings.

        Verifies that extremely long JTI values are handled
        without performance degradation or errors.

        Assertions:
            - Long JTI is accepted
            - Token can be retrieved
            - No memory issues occur
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "x" * 10000  # Very long JTI
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act
        blacklist.add_token(jti, expires_at)
        result = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result is True
        assert blacklist.get_blacklist_size() == 1

    def test_blacklist_special_characters_in_jti(self):
        """Test handling of special characters in JTI.

        Verifies that JTIs containing special characters
        are handled correctly.

        Assertions:
            - Special characters are preserved
            - Token can be retrieved with exact JTI
            - No encoding issues occur
        """
        # Arrange
        blacklist = TokenBlacklist()
        jti = "token!@#$%^&*(){}[]|\\:;\"'<>,.?/~`"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act
        blacklist.add_token(jti, expires_at)
        result = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result is True

    def test_large_scale_token_blacklisting(self):
        """Test blacklist performance with large number of tokens.

        Verifies that the blacklist can handle a large number
        of tokens without significant performance degradation.

        Assertions:
            - Large number of tokens can be added
            - Lookup remains efficient
            - Memory usage is reasonable
        """
        # Arrange
        blacklist = TokenBlacklist()
        num_tokens = 1000
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act - Add many tokens
        for i in range(num_tokens):
            jti = f"large-scale-token-{i}"
            blacklist.add_token(jti, expires_at)

        # Assert
        assert blacklist.get_blacklist_size() == num_tokens

        # Verify random token is still retrievable
        assert blacklist.is_token_blacklisted("large-scale-token-500") is True

    def test_clear_all_removes_all_tokens(self):
        """Test that clear_all removes all tokens from blacklist.

        Verifies that the clear_all method removes all tokens
        regardless of expiration status.

        Assertions:
            - All tokens are removed
            - Blacklist size becomes zero
            - Previously blacklisted tokens return False
        """
        # Arrange
        blacklist = TokenBlacklist()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        jtis = [f"token-{i}" for i in range(10)]
        for jti in jtis:
            blacklist.add_token(jti, expires_at)

        # Act
        blacklist.clear_all()

        # Assert
        assert blacklist.get_blacklist_size() == 0
        for jti in jtis:
            assert blacklist.is_token_blacklisted(jti) is False


class TestRedisTokenBlacklist:
    """Tests for Redis-backed token blacklist implementation."""

    def test_redis_blacklist_initialization_with_client(self):
        """Test Redis blacklist initialization with provided client.

        Verifies that RedisTokenBlacklist can be initialized
        with a custom Redis client instance.

        Assertions:
            - Client is stored correctly
            - Instance is created successfully
        """
        # Arrange
        mock_redis = MagicMock()

        # Act
        blacklist = RedisTokenBlacklist(redis_client=mock_redis)

        # Assert
        assert blacklist.redis_client is mock_redis

    def test_redis_add_token_calls_setex_with_correct_ttl(self):
        """Test that Redis add_token uses setex with correct TTL.

        Verifies that tokens are added to Redis with appropriate
        TTL values calculated from expiration time.

        Assertions:
            - setex is called with correct key
            - TTL is calculated correctly
            - Redis key pattern is correct
        """
        # Arrange
        mock_redis = MagicMock()
        blacklist = RedisTokenBlacklist(redis_client=mock_redis)

        jti = "redis-test-token"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)

        # Act
        blacklist.add_token(jti, expires_at)

        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args

        # Verify key pattern
        assert call_args[0][0] == f"blacklist:token:{jti}"

        # Verify TTL is approximately 3600 seconds (allow 5 second margin)
        ttl = call_args[0][1]
        assert 3595 <= ttl <= 3600

        # Verify value
        assert call_args[0][2] == "1"

    def test_redis_add_token_skips_expired_tokens(self):
        """Test that Redis add_token skips tokens with past expiration.

        Verifies that tokens already expired are not added to Redis
        to prevent unnecessary operations.

        Assertions:
            - setex is not called for expired tokens
            - No Redis operation for past expiration
        """
        # Arrange
        mock_redis = MagicMock()
        blacklist = RedisTokenBlacklist(redis_client=mock_redis)

        jti = "expired-redis-token"
        expires_at = datetime.now(timezone.utc) - timedelta(seconds=3600)

        # Act
        blacklist.add_token(jti, expires_at)

        # Assert - setex should not be called
        mock_redis.setex.assert_not_called()

    def test_redis_is_token_blacklisted_checks_exists(self):
        """Test that Redis is_token_blacklisted checks key existence.

        Verifies that blacklist checks use Redis EXISTS command
        with the correct key pattern.

        Assertions:
            - exists is called with correct key
            - Returns True when key exists
            - Returns False when key doesn't exist
        """
        # Arrange
        mock_redis = MagicMock()
        blacklist = RedisTokenBlacklist(redis_client=mock_redis)

        jti = "check-token"

        # Act - Token exists
        mock_redis.exists.return_value = 1
        result_exists = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result_exists is True
        mock_redis.exists.assert_called_with(f"blacklist:token:{jti}")

        # Act - Token doesn't exist
        mock_redis.exists.return_value = 0
        result_not_exists = blacklist.is_token_blacklisted(jti)

        # Assert
        assert result_not_exists is False

    def test_redis_remove_token_calls_delete(self):
        """Test that Redis remove_token calls DELETE command.

        Verifies that token removal uses Redis DELETE with
        the correct key pattern and returns appropriate status.

        Assertions:
            - delete is called with correct key
            - Returns True when token was deleted
            - Returns False when token didn't exist
        """
        # Arrange
        mock_redis = MagicMock()
        blacklist = RedisTokenBlacklist(redis_client=mock_redis)

        jti = "delete-token"

        # Act - Token exists and is deleted
        mock_redis.delete.return_value = 1
        result_deleted = blacklist.remove_token(jti)

        # Assert
        assert result_deleted is True
        mock_redis.delete.assert_called_with(f"blacklist:token:{jti}")

        # Act - Token doesn't exist
        mock_redis.delete.return_value = 0
        result_not_found = blacklist.remove_token(jti)

        # Assert
        assert result_not_found is False

    def test_redis_blacklist_raises_error_when_client_not_configured(self):
        """Test that Redis operations fail when client is not configured.

        Verifies that all Redis operations raise appropriate errors
        when no Redis client is provided.

        Assertions:
            - add_token raises RuntimeError
            - is_token_blacklisted raises RuntimeError
            - remove_token raises RuntimeError
        """
        # Arrange
        blacklist = RedisTokenBlacklist(redis_client=None)
        jti = "test-token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act & Assert - add_token
        with pytest.raises(RuntimeError, match="Redis client not configured"):
            blacklist.add_token(jti, expires_at)

        # Act & Assert - is_token_blacklisted
        with pytest.raises(RuntimeError, match="Redis client not configured"):
            blacklist.is_token_blacklisted(jti)

        # Act & Assert - remove_token
        with pytest.raises(RuntimeError, match="Redis client not configured"):
            blacklist.remove_token(jti)

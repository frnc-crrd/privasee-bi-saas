# Stage 1.2 Continuation Guide
# Token Blacklist Module Testing

**Quick Reference for Next Session**

---

## Current Status

✅ **Stage 1.1 Complete:** Cache Module (26 tests passing)
⏳ **Stage 1.2 Next:** Token Blacklist Module

---

## Stage 1.2: Token Blacklist Module

### Target Metrics
- **Current Coverage:** 52%
- **Target Coverage:** 95%
- **Module Path:** `app/core/token_blacklist.py`
- **Test File:** `tests/unit/test_token_blacklist.py` (to be created)
- **Estimated Tests:** 20-25 tests

---

## Module Analysis

### Functions to Test

1. **`add_token_to_blacklist(jti, expires_at)`**
   - Add JWT token ID to blacklist
   - Store expiration timestamp
   - Redis persistence

2. **`is_token_blacklisted(jti)`**
   - Check if token is blacklisted
   - Return boolean result
   - Handle Redis errors

3. **`cleanup_expired_tokens()`**
   - Remove expired tokens from blacklist
   - Optimize storage
   - Schedule periodic cleanup

4. **`get_blacklist_size()`**
   - Return count of blacklisted tokens
   - Monitoring/metrics support

5. **`clear_all_blacklisted_tokens()`**
   - Administrative function
   - Clear entire blacklist
   - Use with caution

---

## Test Plan Structure

### 1. Basic Blacklist Operations (6-8 tests)
```python
class TestTokenBlacklisting:
    """Tests for basic token blacklist operations."""

    def test_add_token_to_blacklist_success()
    def test_add_token_to_blacklist_with_expiration()
    def test_is_token_blacklisted_returns_true()
    def test_is_token_blacklisted_returns_false()
    def test_blacklist_token_persistence()
    def test_blacklist_duplicate_token()
```

### 2. Redis Integration (4-6 tests)
```python
class TestRedisIntegration:
    """Tests for Redis backend integration."""

    def test_redis_connection_success()
    def test_redis_connection_failure_fallback()
    def test_redis_persistence_verification()
    def test_redis_reconnection_after_failure()
```

### 3. Token Expiration & Cleanup (5-7 tests)
```python
class TestTokenExpiration:
    """Tests for token expiration and cleanup."""

    def test_expired_tokens_automatically_cleaned()
    def test_cleanup_removes_only_expired_tokens()
    def test_cleanup_preserves_valid_tokens()
    def test_expiration_ttl_respected()
    def test_manual_cleanup_operation()
```

### 4. Edge Cases & Security (5-6 tests)
```python
class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security scenarios."""

    def test_blacklist_null_jti()
    def test_blacklist_empty_jti()
    def test_blacklist_malformed_jti()
    def test_concurrent_blacklist_operations()
    def test_large_scale_token_blacklisting()
    def test_memory_management_under_load()
```

---

## Commands to Run

### Read the Module
```bash
cat app/core/token_blacklist.py
```

### Create Test File
```bash
# File: tests/unit/test_token_blacklist.py
```

### Run Tests
```bash
pytest tests/unit/test_token_blacklist.py -v --tb=short
```

### Check Coverage
```bash
pytest tests/unit/test_token_blacklist.py --cov=app/core/token_blacklist --cov-report=term-missing
```

---

## Template Structure

```python
"""
Unit tests for token blacklist module.

This module contains comprehensive tests for JWT token blacklisting,
including Redis integration, expiration handling, and security scenarios.

Test Coverage:
    - Token blacklisting operations
    - Redis backend integration
    - Token expiration and cleanup
    - Security and edge cases
    - Performance under load
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
from datetime import datetime, timedelta

from app.core.token_blacklist import (
    add_token_to_blacklist,
    is_token_blacklisted,
    cleanup_expired_tokens,
    get_blacklist_size,
    clear_all_blacklisted_tokens,
)


class TestTokenBlacklisting:
    """Tests for basic token blacklist operations."""

    def test_add_token_to_blacklist_success(self, app):
        """Test that tokens can be added to blacklist.

        Verifies that JWT token IDs (jti) are correctly added to
        the blacklist and can be retrieved.

        Args:
            app: Flask application fixture

        Assertions:
            - Token added successfully
            - Token appears in blacklist
            - Expiration time recorded
        """
        # Test implementation here
        pass

# ... more test classes
```

---

## Quality Checklist

For each test, ensure:

- [ ] Google-style docstring (complete with Args, Assertions)
- [ ] AAA pattern (Arrange-Act-Assert)
- [ ] Clear test name: `test_<component>_<scenario>_<outcome>`
- [ ] Professional English comments
- [ ] Edge cases considered
- [ ] Error scenarios tested
- [ ] Security implications addressed
- [ ] Performance considerations noted

---

## Expected Outcomes

### Success Criteria
- [ ] 20-25 tests created
- [ ] All tests passing
- [ ] Coverage ≥ 95% for token_blacklist.py
- [ ] No security vulnerabilities
- [ ] Redis failure handling tested
- [ ] Token expiration logic verified

### Deliverables
1. `tests/unit/test_token_blacklist.py` - Comprehensive test file
2. Updated `TESTING_STAGE_1_PROGRESS.md` - Progress report
3. Coverage report showing improvement
4. All tests passing in CI/CD

---

## Critical Security Considerations

⚠️ **Token Blacklist is Critical for Security**

1. **Token Replay Attacks:** Blacklist must prevent reuse of invalidated tokens
2. **Logout Enforcement:** Blacklisted tokens must be rejected immediately
3. **Expiration Handling:** Expired tokens should auto-cleanup to prevent bloat
4. **Redis Failure:** Graceful degradation required (fail secure, not open)
5. **Performance:** Blacklist checks must be fast (< 10ms p95)

---

## Next Steps After 1.2

1. Update progress document
2. Run full test suite
3. Check overall coverage improvement
4. Move to Stage 1.3: Query Monitoring

---

## Quick Start Command

```bash
# Read token blacklist module
cat app/core/token_blacklist.py

# Start creating tests
touch tests/unit/test_token_blacklist.py

# Open in editor and begin implementation
```

---

**Last Updated:** 2025-11-27
**Status:** Ready to Start
**Priority:** HIGH (Security Critical)

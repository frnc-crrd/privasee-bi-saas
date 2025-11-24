"""Core utilities and configuration for the Privasee BI SaaS application.

This module provides foundational infrastructure components:
- Configuration management with environment-based settings
- Structured logging and request context tracking
- Standardized API response wrappers
- Shared utilities used across the application

All core components follow enterprise patterns and are designed for:
- Type safety with full Pydantic validation
- Testability with clear dependency injection
- Observability with structured logging
- Security with validated configurations
"""

from app.core.config import Settings, get_settings
from app.core.context import (
    get_full_context,
    get_request_id,
    get_user_context,
    set_request_id,
    set_user_context,
    setup_request_context,
)
from app.core.logging_config import log_exception, log_request_info, setup_logging
from app.core.responses import (
    bad_request_response,
    conflict_response,
    created_response,
    error_response,
    forbidden_response,
    internal_error_response,
    no_content_response,
    not_found_response,
    paginated_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    # Logging
    "setup_logging",
    "log_request_info",
    "log_exception",
    # Request Context
    "setup_request_context",
    "get_request_id",
    "set_request_id",
    "get_user_context",
    "set_user_context",
    "get_full_context",
    # Response Builders
    "success_response",
    "error_response",
    "paginated_response",
    "created_response",
    "no_content_response",
    "bad_request_response",
    "unauthorized_response",
    "forbidden_response",
    "not_found_response",
    "conflict_response",
    "validation_error_response",
    "internal_error_response",
]

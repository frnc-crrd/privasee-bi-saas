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

__all__ = ["Settings", "get_settings"]

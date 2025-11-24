"""Custom exception hierarchy and error handlers for the application.

This module provides a comprehensive exception system:
- Structured exception hierarchy with HTTP status codes
- Authentication and authorization exceptions
- Validation and schema exceptions
- Database exceptions
- Global Flask error handlers

All exceptions are designed to integrate seamlessly with the standardized
API response format and structured logging.

Usage:
    from app.exceptions import (
        BaseAPIException,
        ValidationError,
        InvalidCredentialsError,
        register_error_handlers
    )

    # In application factory
    app = Flask(__name__)
    register_error_handlers(app)

    # In route handlers
    if not user:
        raise ResourceNotFoundException("User not found", resource_type="User")

    if not valid:
        raise ValidationError(
            "Invalid data",
            field_errors={"email": ["Invalid format"]}
        )
"""

# Base exceptions
# Authentication exceptions
from app.exceptions.auth import (
    AccountInactiveError,
    AuthenticationError,
    AuthorizationError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    ResourceAccessDeniedError,
    TokenExpiredError,
)
from app.exceptions.base import (
    BadRequestException,
    BaseAPIException,
    ConflictException,
    DatabaseException,
    ResourceNotFoundException,
)

# Error handlers
from app.exceptions.handlers import register_error_handlers

# Validation exceptions
from app.exceptions.validation import (
    BusinessRuleViolationError,
    InvalidFormatError,
    RequiredFieldError,
    SchemaValidationError,
    ValidationError,
    ValueRangeError,
)

__all__ = [
    # Base exceptions
    "BaseAPIException",
    "DatabaseException",
    "ResourceNotFoundException",
    "ConflictException",
    "BadRequestException",
    # Authentication exceptions
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "InvalidTokenError",
    "AccountInactiveError",
    # Authorization exceptions
    "AuthorizationError",
    "InsufficientPermissionsError",
    "ResourceAccessDeniedError",
    # Validation exceptions
    "ValidationError",
    "SchemaValidationError",
    "RequiredFieldError",
    "InvalidFormatError",
    "ValueRangeError",
    "BusinessRuleViolationError",
    # Error handlers
    "register_error_handlers",
]

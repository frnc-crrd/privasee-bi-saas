"""Global error handlers for Flask application.

This module provides centralized error handling for all exceptions:
- Custom application exceptions (BaseAPIException)
- Standard Flask/Werkzeug exceptions (404, 405, 500)
- Pydantic validation errors
- SQLAlchemy database errors
- Unexpected exceptions

All errors are logged and converted to standardized API responses.

Usage:
    from app.exceptions.handlers import register_error_handlers

    # In application factory
    app = Flask(__name__)
    register_error_handlers(app)
"""

import logging
from typing import Tuple

from flask import Flask
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound

from app.core.logging_config import log_exception
from app.core.responses import (
    error_response,
    internal_error_response,
    not_found_response,
    validation_error_response,
)
from app.exceptions.auth import AuthenticationError, AuthorizationError
from app.exceptions.base import (
    BadRequestException,
    BaseAPIException,
    ConflictException,
    DatabaseException,
    ResourceNotFoundException,
)
from app.exceptions.validation import SchemaValidationError, ValidationError

logger = logging.getLogger(__name__)


def handle_base_api_exception(error: BaseAPIException) -> Tuple:
    """Handle custom API exceptions.

    Converts BaseAPIException and subclasses to standardized API responses.

    Args:
        error: BaseAPIException instance

    Returns:
        Tuple of (response, status_code)
    """
    # Log the error with context
    logger.warning(
        f"API exception: {error.error_code} - {error.message}",
        extra={
            "error_code": error.error_code,
            "status_code": error.status_code,
            "error_details": error.details,
        },
    )

    return error_response(
        message=error.message,
        status_code=error.status_code,
        error_code=error.error_code,
        details=error.details if error.details else None,
    )


def handle_validation_error(error: ValidationError) -> Tuple:
    """Handle validation errors with field-level details.

    Converts ValidationError to 422 response with field errors.

    Args:
        error: ValidationError instance

    Returns:
        Tuple of (response, status_code)
    """
    # Log validation error
    logger.info(
        f"Validation error: {error.message}",
        extra={
            "field_errors": error.field_errors,
            "details": error.details,
        },
    )

    return validation_error_response(
        message=error.message,
        details={"field_errors": error.field_errors, **error.details},
    )


def handle_pydantic_validation_error(error: PydanticValidationError) -> Tuple:
    """Handle Pydantic validation errors.

    Converts Pydantic ValidationError to SchemaValidationError
    and returns 422 response.

    Args:
        error: Pydantic ValidationError instance

    Returns:
        Tuple of (response, status_code)
    """
    # Convert to SchemaValidationError
    schema_error = SchemaValidationError.from_pydantic(error)

    # Log the error
    logger.info(
        f"Schema validation error: {schema_error.message}",
        extra={
            "field_errors": schema_error.field_errors,
            "error_count": len(error.errors()),
        },
    )

    return validation_error_response(
        message=schema_error.message,
        details={"field_errors": schema_error.field_errors},
    )


def handle_sqlalchemy_integrity_error(error: IntegrityError) -> Tuple:
    """Handle SQLAlchemy integrity constraint violations.

    Converts database constraint errors (unique, foreign key, etc.)
    to 409 Conflict responses.

    Args:
        error: SQLAlchemy IntegrityError instance

    Returns:
        Tuple of (response, status_code)
    """
    # Log the database error
    logger.error(
        "Database integrity constraint violation",
        exc_info=error,
        extra={"error_type": "integrity_error"},
    )

    # Try to extract constraint name from error message
    error_msg = str(error.orig) if hasattr(error, "orig") else str(error)

    # Provide user-friendly message
    if "unique" in error_msg.lower():
        message = "A record with this value already exists"
        error_code = "DUPLICATE_ENTRY"
    elif "foreign key" in error_msg.lower():
        message = "Referenced record does not exist"
        error_code = "INVALID_REFERENCE"
    else:
        message = "Database constraint violation"
        error_code = "CONSTRAINT_VIOLATION"

    return error_response(
        message=message,
        status_code=409,
        error_code=error_code,
        details={"constraint_error": error_msg[:200]},  # Truncate long messages
    )


def handle_sqlalchemy_operational_error(error: OperationalError) -> Tuple:
    """Handle SQLAlchemy operational errors.

    Converts database connection/operational errors to 500 responses.

    Args:
        error: SQLAlchemy OperationalError instance

    Returns:
        Tuple of (response, status_code)
    """
    # Log the operational error
    log_exception(
        error,
        context={"error_type": "database_operational_error"},
    )

    return internal_error_response(
        message="Database operation failed",
    )


def handle_sqlalchemy_error(error: SQLAlchemyError) -> Tuple:
    """Handle generic SQLAlchemy errors.

    Converts general database errors to 500 responses.

    Args:
        error: SQLAlchemyError instance

    Returns:
        Tuple of (response, status_code)
    """
    # Log the database error
    log_exception(
        error,
        context={"error_type": "database_error"},
    )

    return internal_error_response(
        message="Database error occurred",
    )


def handle_werkzeug_not_found(error: NotFound) -> Tuple:
    """Handle Werkzeug 404 Not Found errors.

    Converts Flask 404 errors to standardized API responses.

    Args:
        error: Werkzeug NotFound exception

    Returns:
        Tuple of (response, status_code)
    """
    logger.info(f"Route not found: {error.description}")

    return not_found_response(message="The requested URL was not found on the server")


def handle_werkzeug_method_not_allowed(error: MethodNotAllowed) -> Tuple:
    """Handle Werkzeug 405 Method Not Allowed errors.

    Converts Flask 405 errors to standardized API responses.

    Args:
        error: Werkzeug MethodNotAllowed exception

    Returns:
        Tuple of (response, status_code)
    """
    logger.info(f"Method not allowed: {error.description}")

    allowed_methods = ", ".join(error.valid_methods) if error.valid_methods else "N/A"

    return error_response(
        message="Method not allowed for this endpoint",
        status_code=405,
        error_code="METHOD_NOT_ALLOWED",
        details={"allowed_methods": allowed_methods},
    )


def handle_werkzeug_http_exception(error: HTTPException) -> Tuple:
    """Handle generic Werkzeug HTTP exceptions.

    Converts standard HTTP exceptions (400, 401, 403, etc.)
    to standardized API responses.

    Args:
        error: Werkzeug HTTPException instance

    Returns:
        Tuple of (response, status_code)
    """
    logger.warning(
        f"HTTP exception: {error.code} - {error.name}",
        extra={
            "status_code": error.code,
            "error_name": error.name,
        },
    )

    return error_response(
        message=error.description or error.name,
        status_code=error.code or 500,
        error_code=error.name.upper().replace(" ", "_") if error.name else "HTTP_ERROR",
    )


def handle_unexpected_exception(error: Exception) -> Tuple:
    """Handle unexpected/unhandled exceptions.

    Converts any unhandled exception to 500 response and logs
    full traceback for debugging.

    Args:
        error: Any unhandled Exception

    Returns:
        Tuple of (response, status_code)
    """
    # Log the unexpected exception with full traceback
    log_exception(
        error,
        context={"error_type": "unexpected_exception"},
    )

    # Return generic 500 error (don't expose internal details)
    return internal_error_response(
        message="An unexpected error occurred",
    )


def register_error_handlers(app: Flask) -> None:
    """Register all error handlers with Flask application.

    Sets up handlers for:
    - Custom application exceptions (BaseAPIException)
    - Validation errors (ValidationError, Pydantic)
    - Database errors (SQLAlchemy)
    - HTTP exceptions (404, 405, etc.)
    - Unexpected exceptions

    Args:
        app: Flask application instance

    Returns:
        None

    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> register_error_handlers(app)
    """
    # Custom application exceptions
    app.register_error_handler(BaseAPIException, handle_base_api_exception)
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(AuthenticationError, handle_base_api_exception)
    app.register_error_handler(AuthorizationError, handle_base_api_exception)
    app.register_error_handler(ResourceNotFoundException, handle_base_api_exception)
    app.register_error_handler(ConflictException, handle_base_api_exception)
    app.register_error_handler(BadRequestException, handle_base_api_exception)
    app.register_error_handler(DatabaseException, handle_base_api_exception)

    # Pydantic validation errors
    app.register_error_handler(PydanticValidationError, handle_pydantic_validation_error)

    # SQLAlchemy database errors
    app.register_error_handler(IntegrityError, handle_sqlalchemy_integrity_error)
    app.register_error_handler(OperationalError, handle_sqlalchemy_operational_error)
    app.register_error_handler(SQLAlchemyError, handle_sqlalchemy_error)

    # Werkzeug HTTP exceptions
    app.register_error_handler(NotFound, handle_werkzeug_not_found)
    app.register_error_handler(MethodNotAllowed, handle_werkzeug_method_not_allowed)
    app.register_error_handler(HTTPException, handle_werkzeug_http_exception)

    # Catch-all for unexpected exceptions
    app.register_error_handler(Exception, handle_unexpected_exception)

    logger.info("Error handlers registered successfully")

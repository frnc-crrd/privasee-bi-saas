"""Base exception classes for the application.

This module provides the foundation for a structured exception hierarchy:
- Type-safe exception handling with HTTP status codes
- Machine-readable error codes for client integration
- Optional details for additional context
- Integration with standardized API responses

All custom exceptions should inherit from BaseAPIException to ensure
consistent error handling across the application.

Usage:
    from app.exceptions.base import BaseAPIException

    class CustomError(BaseAPIException):
        def __init__(self, message: str):
            super().__init__(
                message=message,
                status_code=400,
                error_code="CUSTOM_ERROR"
            )

    raise CustomError("Something went wrong")
"""

from http import HTTPStatus
from typing import Any, Dict, Optional


class BaseAPIException(Exception):
    """Base exception class for all API exceptions.

    Provides a consistent structure for exceptions with HTTP status codes,
    error codes, and optional details. All custom exceptions should inherit
    from this class.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 500)
        error_code: Machine-readable error code (default: "API_ERROR")
        details: Optional dictionary with additional context
    """

    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: str = "API_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize base API exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            error_code: Machine-readable error code
            details: Optional additional context

        Example:
            >>> raise BaseAPIException(
            ...     message="Operation failed",
            ...     status_code=400,
            ...     error_code="OPERATION_FAILED",
            ...     details={"operation": "update_user"}
            ... )
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format.

        Returns:
            Dictionary with error information

        Example:
            >>> exc = BaseAPIException("Test error", status_code=400)
            >>> exc.to_dict()
            {
                'message': 'Test error',
                'code': 'API_ERROR',
                'details': {}
            }
        """
        return {
            "message": self.message,
            "code": self.error_code,
            "details": self.details,
        }

    def __str__(self) -> str:
        """String representation of the exception.

        Returns:
            Formatted error message with code
        """
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """Developer-friendly representation of the exception.

        Returns:
            Representation string with all attributes
        """
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r}, "
            f"details={self.details!r})"
        )


class DatabaseException(BaseAPIException):
    """Exception raised for database-related errors.

    Used for connection errors, query failures, constraint violations,
    and other database-related issues.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 500)
        error_code: Machine-readable error code (default: "DATABASE_ERROR")
        details: Optional dictionary with query/table information
    """

    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize database exception.

        Args:
            message: Human-readable error message
            details: Optional database-specific context (table, query, etc.)

        Example:
            >>> raise DatabaseException(
            ...     message="Failed to insert user",
            ...     details={"table": "users", "constraint": "email_unique"}
            ... )
        """
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details,
        )


class ResourceNotFoundException(BaseAPIException):
    """Exception raised when a requested resource is not found.

    Used for 404 errors when entities don't exist in the database
    or file system.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 404)
        error_code: Machine-readable error code (default: "NOT_FOUND")
        details: Optional dictionary with resource information
    """

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize resource not found exception.

        Args:
            message: Human-readable error message
            resource_type: Type of resource (e.g., "User", "Order")
            resource_id: ID of the missing resource
            details: Optional additional context

        Example:
            >>> raise ResourceNotFoundException(
            ...     message="User not found",
            ...     resource_type="User",
            ...     resource_id=123
            ... )
        """
        exception_details = details or {}
        if resource_type:
            exception_details["resource_type"] = resource_type
        if resource_id is not None:
            exception_details["resource_id"] = resource_id

        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            error_code="NOT_FOUND",
            details=exception_details,
        )


class ConflictException(BaseAPIException):
    """Exception raised when a resource conflict occurs.

    Used for 409 errors such as duplicate entries, concurrent modifications,
    or business rule violations.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 409)
        error_code: Machine-readable error code (default: "CONFLICT")
        details: Optional dictionary with conflict information
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize conflict exception.

        Args:
            message: Human-readable error message
            details: Optional conflict-specific context

        Example:
            >>> raise ConflictException(
            ...     message="Email already exists",
            ...     details={"field": "email", "value": "user@example.com"}
            ... )
        """
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class BadRequestException(BaseAPIException):
    """Exception raised for malformed or invalid requests.

    Used for 400 errors when client sends invalid data that doesn't
    pass basic validation.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 400)
        error_code: Machine-readable error code (default: "BAD_REQUEST")
        details: Optional dictionary with request issues
    """

    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize bad request exception.

        Args:
            message: Human-readable error message
            details: Optional request-specific context

        Example:
            >>> raise BadRequestException(
            ...     message="Missing required field",
            ...     details={"field": "email"}
            ... )
        """
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            error_code="BAD_REQUEST",
            details=details,
        )

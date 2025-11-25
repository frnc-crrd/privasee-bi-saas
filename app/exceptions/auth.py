"""Authentication and authorization exception classes.

This module provides exceptions for auth-related errors:
- Authentication failures (invalid credentials, expired tokens)
- Authorization failures (insufficient permissions, forbidden access)
- Account state issues (inactive, locked, suspended)

All exceptions integrate with Flask-Login and Flask-JWT-Extended for
consistent error handling across authentication mechanisms.

Usage:
    from app.exceptions.auth import AuthenticationError, InsufficientPermissionsError

    # Authentication failure
    if not user.check_password(password):
        raise InvalidCredentialsError("Invalid email or password")

    # Authorization failure
    if user.role not in allowed_roles:
        raise InsufficientPermissionsError(
            f"Required roles: {', '.join(allowed_roles)}"
        )
"""

from http import HTTPStatus
from typing import Any, Dict, Optional

from app.exceptions.base import BaseAPIException


class AuthenticationError(BaseAPIException):
    """Base exception for authentication failures.

    Used when user identity cannot be verified (invalid credentials,
    expired tokens, missing authentication).

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 401)
        error_code: Machine-readable error code (default: "AUTHENTICATION_ERROR")
        details: Optional dictionary with auth-specific context
    """

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "AUTHENTICATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize authentication error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Optional authentication context

        Example:
            >>> raise AuthenticationError(
            ...     message="Invalid token",
            ...     error_code="INVALID_TOKEN"
            ... )
        """
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            error_code=error_code,
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Exception raised when login credentials are invalid.

    Used for incorrect email/password combinations.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 401)
        error_code: Machine-readable error code (default: "INVALID_CREDENTIALS")
    """

    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize invalid credentials error.

        Args:
            message: Human-readable error message
            details: Optional login attempt context

        Example:
            >>> raise InvalidCredentialsError("Invalid email or password")
        """
        super().__init__(
            message=message,
            error_code="INVALID_CREDENTIALS",
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """Exception raised when authentication token has expired.

    Used for expired JWT tokens or session tokens.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 401)
        error_code: Machine-readable error code (default: "TOKEN_EXPIRED")
    """

    def __init__(
        self,
        message: str = "Authentication token has expired",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize token expired error.

        Args:
            message: Human-readable error message
            details: Optional token information

        Example:
            >>> raise TokenExpiredError(
            ...     "Your session has expired. Please login again.",
            ...     details={"expired_at": "2025-11-24T10:00:00Z"}
            ... )
        """
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            details=details,
        )


class InvalidTokenError(AuthenticationError):
    """Exception raised when authentication token is invalid or malformed.

    Used for corrupted, tampered, or incorrectly formatted tokens.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 401)
        error_code: Machine-readable error code (default: "INVALID_TOKEN")
    """

    def __init__(
        self,
        message: str = "Invalid authentication token",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize invalid token error.

        Args:
            message: Human-readable error message
            details: Optional token validation context

        Example:
            >>> raise InvalidTokenError(
            ...     "Token signature verification failed",
            ...     details={"reason": "signature_mismatch"}
            ... )
        """
        super().__init__(
            message=message,
            error_code="INVALID_TOKEN",
            details=details,
        )


class AccountInactiveError(AuthenticationError):
    """Exception raised when user account is inactive or disabled.

    Used when user exists but account is not active.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 401)
        error_code: Machine-readable error code (default: "ACCOUNT_INACTIVE")
    """

    def __init__(
        self,
        message: str = "Account is inactive or disabled",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize account inactive error.

        Args:
            message: Human-readable error message
            details: Optional account state information

        Example:
            >>> raise AccountInactiveError(
            ...     "Your account has been disabled",
            ...     details={"user_id": 123, "disabled_at": "2025-11-20"}
            ... )
        """
        super().__init__(
            message=message,
            error_code="ACCOUNT_INACTIVE",
            details=details,
        )


class AuthorizationError(BaseAPIException):
    """Base exception for authorization failures.

    Used when authenticated user lacks permission to access a resource
    or perform an action.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 403)
        error_code: Machine-readable error code (default: "AUTHORIZATION_ERROR")
        details: Optional dictionary with permission context
    """

    def __init__(
        self,
        message: str = "Access denied",
        error_code: str = "AUTHORIZATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize authorization error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Optional permission context

        Example:
            >>> raise AuthorizationError(
            ...     message="Admin access required",
            ...     error_code="ADMIN_REQUIRED"
            ... )
        """
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            error_code=error_code,
            details=details,
        )


class InsufficientPermissionsError(AuthorizationError):
    """Exception raised when user lacks required permissions.

    Used for role-based access control (RBAC) violations.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 403)
        error_code: Machine-readable error code (default: "INSUFFICIENT_PERMISSIONS")
    """

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_roles: Optional[list[str]] = None,
        user_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize insufficient permissions error.

        Args:
            message: Human-readable error message
            required_roles: List of roles that would grant access
            user_role: Current user's role
            details: Optional permission context

        Example:
            >>> raise InsufficientPermissionsError(
            ...     message="Admin or analyst role required",
            ...     required_roles=["admin", "analyst"],
            ...     user_role="viewer"
            ... )
        """
        exception_details = details or {}
        if required_roles:
            exception_details["required_roles"] = required_roles
        if user_role:
            exception_details["user_role"] = user_role

        super().__init__(
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            details=exception_details,
        )


class ResourceAccessDeniedError(AuthorizationError):
    """Exception raised when user cannot access specific resource.

    Used for ownership-based or resource-level permission checks.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 403)
        error_code: Machine-readable error code (default: "RESOURCE_ACCESS_DENIED")
    """

    def __init__(
        self,
        message: str = "Access to this resource is denied",
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize resource access denied error.

        Args:
            message: Human-readable error message
            resource_type: Type of resource (e.g., "Order", "Report")
            resource_id: ID of the restricted resource
            details: Optional access context

        Example:
            >>> raise ResourceAccessDeniedError(
            ...     message="You can only view your own orders",
            ...     resource_type="Order",
            ...     resource_id=456
            ... )
        """
        exception_details = details or {}
        if resource_type:
            exception_details["resource_type"] = resource_type
        if resource_id is not None:
            exception_details["resource_id"] = resource_id

        super().__init__(
            message=message,
            error_code="RESOURCE_ACCESS_DENIED",
            details=exception_details,
        )


class UserAlreadyExistsError(BaseAPIException):
    """Exception raised when attempting to create a user that already exists.

    Used for duplicate email or username during registration.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 409 Conflict)
        error_code: Machine-readable error code (default: "USER_ALREADY_EXISTS")
    """

    def __init__(
        self,
        message: str = "User already exists",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize user already exists error.

        Args:
            message: Human-readable error message
            details: Optional context about the conflict

        Example:
            >>> raise UserAlreadyExistsError(
            ...     message="Email address is already registered",
            ...     details={"field": "email"}
            ... )
        """
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            error_code="USER_ALREADY_EXISTS",
            details=details,
        )


# Aliases for backward compatibility
ExpiredTokenError = TokenExpiredError

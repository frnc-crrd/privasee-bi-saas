"""Validation and schema exception classes.

This module provides exceptions for data validation errors:
- Field-level validation failures
- Schema validation errors (Pydantic, Marshmallow)
- Business rule violations
- Data format errors

Integrates with Pydantic for automatic validation error conversion.

Usage:
    from app.exceptions.validation import ValidationError, SchemaValidationError

    # Field validation error
    if not email_is_valid(email):
        raise ValidationError(
            message="Invalid email format",
            field_errors={"email": ["Must be a valid email address"]}
        )

    # Schema validation error
    try:
        UserSchema(**data)
    except PydanticValidationError as e:
        raise SchemaValidationError.from_pydantic(e)
"""

from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

from app.exceptions.base import BaseAPIException


class ValidationError(BaseAPIException):
    """Base exception for validation failures.

    Used for data validation errors with field-level error details.
    Returns 422 Unprocessable Entity status code.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 422)
        error_code: Machine-readable error code (default: "VALIDATION_ERROR")
        field_errors: Dictionary mapping field names to error messages
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message
            field_errors: Dictionary mapping field names to error lists
            details: Optional validation context

        Example:
            >>> raise ValidationError(
            ...     message="Invalid user data",
            ...     field_errors={
            ...         "email": ["Invalid email format"],
            ...         "password": ["Must be at least 8 characters"]
            ...     }
            ... )
        """
        exception_details = details or {}
        if field_errors:
            exception_details["field_errors"] = field_errors

        super().__init__(
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=exception_details,
        )
        self.field_errors = field_errors or {}


class SchemaValidationError(ValidationError):
    """Exception raised for schema validation failures.

    Used when data doesn't conform to expected schema (Pydantic, Marshmallow).
    Provides helper method to convert Pydantic validation errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 422)
        error_code: Machine-readable error code (default: "SCHEMA_VALIDATION_ERROR")
        field_errors: Dictionary mapping field names to error messages
    """

    def __init__(
        self,
        message: str = "Schema validation failed",
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize schema validation error.

        Args:
            message: Human-readable error message
            field_errors: Dictionary mapping field names to error lists
            details: Optional schema context

        Example:
            >>> raise SchemaValidationError(
            ...     message="Invalid request body",
            ...     field_errors={"age": ["Must be a positive integer"]}
            ... )
        """
        exception_details = details or {}
        exception_details["error_type"] = "schema_validation"

        super().__init__(
            message=message,
            field_errors=field_errors,
            details=exception_details,
        )
        self.error_code = "SCHEMA_VALIDATION_ERROR"

    @classmethod
    def from_pydantic(cls, pydantic_error: Any) -> "SchemaValidationError":
        """Create SchemaValidationError from Pydantic ValidationError.

        Args:
            pydantic_error: Pydantic ValidationError instance

        Returns:
            SchemaValidationError with field errors from Pydantic

        Example:
            >>> from pydantic import ValidationError as PydanticError
            >>> try:
            ...     UserSchema(**invalid_data)
            ... except PydanticError as e:
            ...     raise SchemaValidationError.from_pydantic(e)
        """
        field_errors: Dict[str, List[str]] = {}

        for error in pydantic_error.errors():
            # Get field path (e.g., "user.email" or "items.0.price")
            field_path = ".".join(str(loc) for loc in error["loc"])

            # Get error message
            error_msg = error["msg"]

            # Add to field_errors dict
            if field_path not in field_errors:
                field_errors[field_path] = []
            field_errors[field_path].append(error_msg)

        return cls(
            message="Request validation failed",
            field_errors=field_errors,
            details={"error_count": len(pydantic_error.errors())},
        )


class RequiredFieldError(ValidationError):
    """Exception raised when required field is missing.

    Used for missing mandatory fields in request data.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 422)
        error_code: Machine-readable error code (default: "REQUIRED_FIELD_ERROR")
    """

    def __init__(
        self,
        field_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize required field error.

        Args:
            field_name: Name of the missing field
            message: Optional custom error message
            details: Optional validation context

        Example:
            >>> raise RequiredFieldError("email")
            >>> raise RequiredFieldError(
            ...     "password",
            ...     message="Password is required for registration"
            ... )
        """
        error_message = message or f"Field '{field_name}' is required"
        field_errors = {field_name: ["This field is required"]}

        super().__init__(
            message=error_message,
            field_errors=field_errors,
            details=details,
        )
        self.error_code = "REQUIRED_FIELD_ERROR"


class InvalidFormatError(ValidationError):
    """Exception raised when field value has invalid format.

    Used for format validation failures (email, phone, date, etc.).

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 422)
        error_code: Machine-readable error code (default: "INVALID_FORMAT_ERROR")
    """

    def __init__(
        self,
        field_name: str,
        expected_format: str,
        actual_value: Optional[Any] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize invalid format error.

        Args:
            field_name: Name of the field with invalid format
            expected_format: Description of expected format
            actual_value: The invalid value (optional, for logging)
            message: Optional custom error message
            details: Optional validation context

        Example:
            >>> raise InvalidFormatError(
            ...     field_name="email",
            ...     expected_format="valid email address",
            ...     actual_value="not-an-email"
            ... )
        """
        error_message = message or f"Field '{field_name}' has invalid format"
        field_errors = {field_name: [f"Expected format: {expected_format}"]}

        exception_details = details or {}
        exception_details["expected_format"] = expected_format
        if actual_value is not None:
            exception_details["actual_value"] = str(actual_value)

        super().__init__(
            message=error_message,
            field_errors=field_errors,
            details=exception_details,
        )
        self.error_code = "INVALID_FORMAT_ERROR"


class ValueRangeError(ValidationError):
    """Exception raised when field value is outside valid range.

    Used for numeric range, string length, or date range validation failures.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 422)
        error_code: Machine-readable error code (default: "VALUE_RANGE_ERROR")
    """

    def __init__(
        self,
        field_name: str,
        min_value: Optional[Union[int, float, str]] = None,
        max_value: Optional[Union[int, float, str]] = None,
        actual_value: Optional[Any] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize value range error.

        Args:
            field_name: Name of the field with invalid range
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            actual_value: The invalid value
            message: Optional custom error message
            details: Optional validation context

        Example:
            >>> raise ValueRangeError(
            ...     field_name="age",
            ...     min_value=18,
            ...     max_value=120,
            ...     actual_value=150
            ... )
        """
        if message is None:
            if min_value is not None and max_value is not None:
                error_message = f"Field '{field_name}' must be between {min_value} and {max_value}"
                range_desc = f"between {min_value} and {max_value}"
            elif min_value is not None:
                error_message = f"Field '{field_name}' must be at least {min_value}"
                range_desc = f"at least {min_value}"
            elif max_value is not None:
                error_message = f"Field '{field_name}' must be at most {max_value}"
                range_desc = f"at most {max_value}"
            else:
                error_message = f"Field '{field_name}' is outside valid range"
                range_desc = "valid range"
        else:
            error_message = message
            range_desc = "see details"

        field_errors = {field_name: [f"Value must be {range_desc}"]}

        exception_details = details or {}
        if min_value is not None:
            exception_details["min_value"] = min_value
        if max_value is not None:
            exception_details["max_value"] = max_value
        if actual_value is not None:
            exception_details["actual_value"] = actual_value

        super().__init__(
            message=error_message,
            field_errors=field_errors,
            details=exception_details,
        )
        self.error_code = "VALUE_RANGE_ERROR"


class BusinessRuleViolationError(ValidationError):
    """Exception raised when business rule is violated.

    Used for domain-specific validation failures that go beyond
    simple format or range checks.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 422)
        error_code: Machine-readable error code (default: "BUSINESS_RULE_VIOLATION")
    """

    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize business rule violation error.

        Args:
            message: Human-readable error message describing the violation
            rule_name: Name of the violated business rule
            details: Optional business context

        Example:
            >>> raise BusinessRuleViolationError(
            ...     message="Cannot delete order with pending payment",
            ...     rule_name="order_deletion_policy",
            ...     details={"order_id": 123, "status": "pending_payment"}
            ... )
        """
        exception_details = details or {}
        if rule_name:
            exception_details["rule_name"] = rule_name

        super().__init__(
            message=message,
            field_errors={},
            details=exception_details,
        )
        self.error_code = "BUSINESS_RULE_VIOLATION"

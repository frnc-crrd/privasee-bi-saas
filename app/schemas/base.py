"""Base schema classes with common fields and configurations.

This module provides foundation classes for all Pydantic schemas:
- BaseSchema with common configuration
- TimestampMixin for created_at/updated_at fields
- PaginationSchema for paginated responses
- MessageResponseSchema for simple success/error messages

All schemas inherit from these base classes to ensure consistency.

Usage:
    from app.schemas.base import BaseSchema, TimestampMixin

    class UserSchema(BaseSchema, TimestampMixin):
        id: int
        username: str
        email: EmailStr
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Type variable for generic pagination
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base Pydantic schema with common configuration.

    All application schemas should inherit from this class to ensure
    consistent behavior across the codebase.

    Attributes:
        Configuration for JSON serialization, validation, and ORM mode
    """

    model_config = ConfigDict(
        # Allow population from ORM models (SQLAlchemy)
        from_attributes=True,
        # Validate field types strictly
        strict=False,
        # Use enum values instead of enum instances
        use_enum_values=True,
        # Validate assignment after model creation
        validate_assignment=True,
        # Allow arbitrary types (for datetime, etc.)
        arbitrary_types_allowed=False,
        # JSON schema customization
        json_schema_extra={
            "example": {},
        },
    )


class TimestampMixin(BaseModel):
    """Mixin for schemas with created_at and updated_at timestamps.

    Use this mixin for schemas representing database models that track
    creation and modification times.

    Attributes:
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    created_at: datetime = Field(
        ...,
        description="Timestamp when the record was created",
        examples=["2025-11-24T10:30:00.000Z"],
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the record was last updated",
        examples=["2025-11-24T15:45:00.000Z"],
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        }
    )


class IDMixin(BaseModel):
    """Mixin for schemas with database ID field.

    Use this mixin for schemas representing persisted entities.

    Attributes:
        id: Unique database identifier
    """

    id: int = Field(
        ...,
        description="Unique identifier",
        gt=0,
        examples=[123],
    )


class PaginationMetadata(BaseSchema):
    """Pagination metadata for paginated responses.

    Contains information about the current page, total pages, and
    navigation flags.

    Attributes:
        page: Current page number (1-indexed)
        per_page: Items per page
        total: Total number of items across all pages
        pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """

    page: int = Field(
        ...,
        description="Current page number (1-indexed)",
        ge=1,
        examples=[1],
    )
    per_page: int = Field(
        ...,
        description="Number of items per page",
        ge=1,
        le=100,
        examples=[10],
    )
    total: int = Field(
        ...,
        description="Total number of items",
        ge=0,
        examples=[250],
    )
    pages: int = Field(
        ...,
        description="Total number of pages",
        ge=0,
        examples=[25],
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page",
        examples=[True],
    )
    has_prev: bool = Field(
        ...,
        description="Whether there is a previous page",
        examples=[False],
    )


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response schema.

    Wraps a list of items with pagination metadata.

    Type Parameters:
        T: Type of items in the response

    Attributes:
        items: List of items for the current page
        pagination: Pagination metadata

    Example:
        >>> from app.schemas.user_schemas import UserResponse
        >>> response = PaginatedResponse[UserResponse](
        ...     items=[UserResponse(...), UserResponse(...)],
        ...     pagination=PaginationMetadata(
        ...         page=1, per_page=10, total=50, pages=5,
        ...         has_next=True, has_prev=False
        ...     )
        ... )
    """

    items: List[T] = Field(
        ...,
        description="List of items for the current page",
    )
    pagination: PaginationMetadata = Field(
        ...,
        description="Pagination metadata",
    )


class MessageResponse(BaseSchema):
    """Simple message response schema.

    Used for endpoints that return only a success/error message
    without additional data.

    Attributes:
        message: Response message
        success: Whether the operation was successful

    Example:
        >>> response = MessageResponse(
        ...     message="User deleted successfully",
        ...     success=True
        ... )
    """

    message: str = Field(
        ...,
        description="Response message",
        min_length=1,
        examples=["Operation completed successfully"],
    )
    success: bool = Field(
        True,
        description="Whether the operation was successful",
        examples=[True],
    )


class ErrorDetail(BaseSchema):
    """Detailed error information.

    Used in error responses to provide structured error details.

    Attributes:
        field: Field name that caused the error (optional)
        message: Error message
        code: Error code (optional)

    Example:
        >>> error = ErrorDetail(
        ...     field="email",
        ...     message="Invalid email format",
        ...     code="INVALID_FORMAT"
        ... )
    """

    field: Optional[str] = Field(
        None,
        description="Field name that caused the error",
        examples=["email"],
    )
    message: str = Field(
        ...,
        description="Error message",
        examples=["Invalid email format"],
    )
    code: Optional[str] = Field(
        None,
        description="Machine-readable error code",
        examples=["INVALID_FORMAT"],
    )


class ErrorResponse(BaseSchema):
    """Standard error response schema.

    Used to return structured error information to clients.

    Attributes:
        message: Main error message
        errors: List of detailed errors (optional)
        code: Machine-readable error code

    Example:
        >>> error = ErrorResponse(
        ...     message="Validation failed",
        ...     code="VALIDATION_ERROR",
        ...     errors=[
        ...         ErrorDetail(field="email", message="Invalid format"),
        ...         ErrorDetail(field="password", message="Too short")
        ...     ]
        ... )
    """

    message: str = Field(
        ...,
        description="Main error message",
        examples=["Validation failed"],
    )
    code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["VALIDATION_ERROR"],
    )
    errors: Optional[List[ErrorDetail]] = Field(
        None,
        description="List of detailed errors",
    )


class HealthCheckResponse(BaseSchema):
    """Health check response schema.

    Used for service health monitoring endpoints.

    Attributes:
        status: Service status (healthy, degraded, unhealthy)
        timestamp: Current server timestamp
        version: Application version
        details: Additional health check details

    Example:
        >>> health = HealthCheckResponse(
        ...     status="healthy",
        ...     timestamp=datetime.utcnow(),
        ...     version="1.0.0",
        ...     details={"database": "connected", "cache": "connected"}
        ... )
    """

    status: str = Field(
        ...,
        description="Service status",
        pattern="^(healthy|degraded|unhealthy)$",
        examples=["healthy"],
    )
    timestamp: datetime = Field(
        ...,
        description="Current server timestamp",
    )
    version: Optional[str] = Field(
        None,
        description="Application version",
        examples=["1.0.0"],
    )
    details: Optional[dict[str, Any]] = Field(
        None,
        description="Additional health check details",
        examples=[{"database": "connected", "cache": "connected"}],
    )

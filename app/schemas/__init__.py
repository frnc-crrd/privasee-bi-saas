"""Pydantic schemas for data validation and serialization.

This module provides all DTOs (Data Transfer Objects) for the application:
- Base schemas and mixins
- Authentication schemas
- User management schemas
- Custom validators

All schemas use Pydantic for runtime validation and automatic documentation.

Usage:
    from app.schemas import (
        LoginRequest,
        TokenResponse,
        UserResponse,
        UserUpdateRequest
    )

    # Validate request data
    login_data = LoginRequest(**request.json)

    # Serialize response data
    user = User.query.get(user_id)
    return UserResponse.model_validate(user)
"""

# Base schemas and utilities
# Authentication schemas
from app.schemas.auth_schemas import (
    AuthStatusResponse,
    ChangePasswordRequest,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.base import (
    BaseSchema,
    ErrorDetail,
    ErrorResponse,
    HealthCheckResponse,
    IDMixin,
    MessageResponse,
    PaginatedResponse,
    PaginationMetadata,
    TimestampMixin,
)

# User schemas
from app.schemas.user_schemas import (
    UserCreateRequest,
    UserFilterParams,
    UserListItemResponse,
    UserPaginatedResponse,
    UserProfileUpdateRequest,
    UserResponse,
    UserStatsResponse,
    UserUpdateRequest,
)

# Validators
from app.schemas.validators import (
    sanitize_string,
    validate_date_range,
    validate_email_format,
    validate_pagination_params,
    validate_password_strength,
    validate_positive_integer,
    validate_role,
    validate_username,
)

__all__ = [
    # Base schemas
    "BaseSchema",
    "IDMixin",
    "TimestampMixin",
    "PaginationMetadata",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthCheckResponse",
    # Authentication schemas
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirmRequest",
    "ChangePasswordRequest",
    "EmailVerificationRequest",
    "LogoutRequest",
    "AuthStatusResponse",
    # User schemas
    "UserResponse",
    "UserListItemResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserProfileUpdateRequest",
    "UserFilterParams",
    "UserPaginatedResponse",
    "UserStatsResponse",
    # Validators
    "validate_password_strength",
    "validate_username",
    "validate_email_format",
    "validate_role",
    "validate_date_range",
    "validate_positive_integer",
    "validate_pagination_params",
    "sanitize_string",
]

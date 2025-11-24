"""User management schema definitions.

This module provides Pydantic schemas for user operations:
- User retrieval and listing
- User creation and updates
- User profile management
- User filtering and search

All schemas exclude sensitive information (passwords) from responses.

Usage:
    from app.schemas.user_schemas import UserResponse, UserUpdateRequest

    # In user endpoint
    @app.route("/api/v1/users/<int:user_id>")
    def get_user(user_id):
        user = User.query.get(user_id)
        return UserResponse.model_validate(user)
"""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema, IDMixin, PaginatedResponse, TimestampMixin
from app.schemas.validators import (
    validate_email_format,
    validate_role,
    validate_username,
)


class UserBase(BaseSchema):
    """Base user schema with common fields.

    Contains fields shared across all user schemas.

    Attributes:
        username: User's username
        email: User's email address
        role: User's role (admin, viewer, analyst)
    """

    username: str = Field(
        ...,
        description="User's username",
        min_length=3,
        max_length=30,
        examples=["john_doe"],
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["john@example.com"],
    )
    role: str = Field(
        ...,
        description="User's role",
        pattern="^(admin|viewer|analyst)$",
        examples=["analyst"],
    )


class UserResponse(UserBase, IDMixin, TimestampMixin):
    """Complete user response schema.

    Returned when fetching individual user details.
    Excludes sensitive information (password hash).

    Attributes:
        id: User's unique identifier
        username: User's username
        email: User's email address
        role: User's role
        is_active: Whether user account is active
        last_login: Last login timestamp
        created_at: Account creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> user = UserResponse(
        ...     id=123,
        ...     username="john_doe",
        ...     email="john@example.com",
        ...     role="analyst",
        ...     is_active=True,
        ...     last_login=datetime(2025, 11, 24, 10, 0),
        ...     created_at=datetime(2025, 11, 1, 9, 0),
        ...     updated_at=datetime(2025, 11, 24, 10, 0)
        ... )
    """

    is_active: bool = Field(
        ...,
        description="Whether user account is active",
        examples=[True],
    )
    last_login: Optional[datetime] = Field(
        None,
        description="Last login timestamp",
        examples=["2025-11-24T10:00:00Z"],
    )


class UserListItemResponse(UserBase, IDMixin):
    """Compact user response for list views.

    Used in paginated user lists with minimal information.

    Attributes:
        id: User's unique identifier
        username: User's username
        email: User's email address
        role: User's role
        is_active: Whether user account is active
        created_at: Account creation timestamp

    Example:
        >>> user = UserListItemResponse(
        ...     id=123,
        ...     username="john_doe",
        ...     email="john@example.com",
        ...     role="analyst",
        ...     is_active=True,
        ...     created_at=datetime(2025, 11, 1, 9, 0)
        ... )
    """

    is_active: bool = Field(
        ...,
        description="Whether user account is active",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        examples=["2025-11-01T09:00:00Z"],
    )


class UserCreateRequest(BaseSchema):
    """Schema for creating a new user (admin only).

    Allows administrators to create user accounts with specific roles.

    Attributes:
        username: User's username
        email: User's email address
        password: Initial password
        role: User's role
        is_active: Whether account starts active (default: True)

    Example:
        >>> user = UserCreateRequest(
        ...     username="new_user",
        ...     email="newuser@example.com",
        ...     password="TempP@ss123",
        ...     role="viewer",
        ...     is_active=True
        ... )
    """

    username: str = Field(
        ...,
        description="User's username",
        min_length=3,
        max_length=30,
        examples=["new_user"],
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["newuser@example.com"],
    )
    password: str = Field(
        ...,
        description="Initial password",
        min_length=8,
        max_length=128,
        examples=["TempP@ss123"],
    )
    role: str = Field(
        "viewer",
        description="User's role",
        pattern="^(admin|viewer|analyst)$",
        examples=["viewer"],
    )
    is_active: bool = Field(
        True,
        description="Whether account starts active",
        examples=[True],
    )

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        """Validate username format."""
        return validate_username(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        return validate_email_format(v)

    @field_validator("role")
    @classmethod
    def validate_role_value(cls, v: str) -> str:
        """Validate role value."""
        return validate_role(v)


class UserUpdateRequest(BaseSchema):
    """Schema for updating user information (admin only).

    Allows administrators to update any user's information.
    All fields are optional.

    Attributes:
        username: New username (optional)
        email: New email address (optional)
        role: New role (optional)
        is_active: New active status (optional)

    Example:
        >>> update = UserUpdateRequest(
        ...     role="admin",
        ...     is_active=False
        ... )
    """

    username: Optional[str] = Field(
        None,
        description="New username",
        min_length=3,
        max_length=30,
        examples=["updated_username"],
    )
    email: Optional[EmailStr] = Field(
        None,
        description="New email address",
        examples=["newemail@example.com"],
    )
    role: Optional[str] = Field(
        None,
        description="New role",
        pattern="^(admin|viewer|analyst)$",
        examples=["admin"],
    )
    is_active: Optional[bool] = Field(
        None,
        description="New active status",
        examples=[False],
    )

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format if provided."""
        if v is not None:
            return validate_username(v)
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None:
            return validate_email_format(v)
        return v

    @field_validator("role")
    @classmethod
    def validate_role_value(cls, v: Optional[str]) -> Optional[str]:
        """Validate role value if provided."""
        if v is not None:
            return validate_role(v)
        return v


class UserProfileUpdateRequest(BaseSchema):
    """Schema for users updating their own profile.

    Allows users to update their own username and email.
    Cannot change role or active status.

    Attributes:
        username: New username (optional)
        email: New email address (optional)

    Example:
        >>> update = UserProfileUpdateRequest(
        ...     username="new_username",
        ...     email="newemail@example.com"
        ... )
    """

    username: Optional[str] = Field(
        None,
        description="New username",
        min_length=3,
        max_length=30,
        examples=["new_username"],
    )
    email: Optional[EmailStr] = Field(
        None,
        description="New email address",
        examples=["newemail@example.com"],
    )

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format if provided."""
        if v is not None:
            return validate_username(v)
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None:
            return validate_email_format(v)
        return v


class UserFilterParams(BaseSchema):
    """Schema for user list filtering and search parameters.

    Used for filtering and searching users in list endpoints.

    Attributes:
        role: Filter by role (optional)
        is_active: Filter by active status (optional)
        search: Search term for username or email (optional)
        created_after: Filter users created after date (optional)
        created_before: Filter users created before date (optional)

    Example:
        >>> filters = UserFilterParams(
        ...     role="analyst",
        ...     is_active=True,
        ...     search="john"
        ... )
    """

    role: Optional[str] = Field(
        None,
        description="Filter by role",
        pattern="^(admin|viewer|analyst)$",
        examples=["analyst"],
    )
    is_active: Optional[bool] = Field(
        None,
        description="Filter by active status",
        examples=[True],
    )
    search: Optional[str] = Field(
        None,
        description="Search term for username or email",
        min_length=1,
        max_length=100,
        examples=["john"],
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Filter users created after this date",
        examples=["2025-01-01T00:00:00Z"],
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Filter users created before this date",
        examples=["2025-12-31T23:59:59Z"],
    )

    @field_validator("role")
    @classmethod
    def validate_role_value(cls, v: Optional[str]) -> Optional[str]:
        """Validate role value if provided."""
        if v is not None:
            return validate_role(v)
        return v


class UserPaginatedResponse(PaginatedResponse[UserListItemResponse]):
    """Paginated response for user lists.

    Wrapper for paginated user list responses.

    Example:
        >>> response = UserPaginatedResponse(
        ...     items=[
        ...         UserListItemResponse(...),
        ...         UserListItemResponse(...)
        ...     ],
        ...     pagination=PaginationMetadata(...)
        ... )
    """

    pass


class UserStatsResponse(BaseSchema):
    """Schema for user statistics.

    Provides aggregate statistics about users.

    Attributes:
        total_users: Total number of users
        active_users: Number of active users
        inactive_users: Number of inactive users
        users_by_role: Count of users per role
        recent_registrations: Number of users registered in last 30 days

    Example:
        >>> stats = UserStatsResponse(
        ...     total_users=100,
        ...     active_users=85,
        ...     inactive_users=15,
        ...     users_by_role={"admin": 5, "analyst": 30, "viewer": 65},
        ...     recent_registrations=12
        ... )
    """

    total_users: int = Field(
        ...,
        description="Total number of users",
        ge=0,
        examples=[100],
    )
    active_users: int = Field(
        ...,
        description="Number of active users",
        ge=0,
        examples=[85],
    )
    inactive_users: int = Field(
        ...,
        description="Number of inactive users",
        ge=0,
        examples=[15],
    )
    users_by_role: dict[str, int] = Field(
        ...,
        description="Count of users per role",
        examples=[{"admin": 5, "analyst": 30, "viewer": 65}],
    )
    recent_registrations: int = Field(
        ...,
        description="Number of users registered in last 30 days",
        ge=0,
        examples=[12],
    )

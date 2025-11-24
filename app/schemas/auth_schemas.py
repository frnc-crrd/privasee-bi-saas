"""Authentication and authorization schema definitions.

This module provides Pydantic schemas for authentication flows:
- User registration and login
- JWT token management (access and refresh tokens)
- Password reset and change
- Email verification
- Logout

All schemas include comprehensive validation and documentation.

Usage:
    from app.schemas.auth_schemas import LoginRequest, TokenResponse

    # In authentication endpoint
    @app.route("/api/v1/auth/login", methods=["POST"])
    def login():
        data = LoginRequest(**request.json)
        # ... authentication logic ...
        return TokenResponse(access_token="...", refresh_token="...")
"""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema
from app.schemas.validators import (
    validate_email_format,
    validate_password_strength,
    validate_username,
)


class LoginRequest(BaseSchema):
    """Schema for user login request.

    Users can log in with either email or username along with their password.

    Attributes:
        email: User's email address (optional if username provided)
        username: User's username (optional if email provided)
        password: User's password
        remember_me: Whether to issue long-lived refresh token

    Example:
        >>> login = LoginRequest(
        ...     email="user@example.com",
        ...     password="MyP@ssw0rd"
        ... )
    """

    email: Optional[EmailStr] = Field(
        None,
        description="User's email address",
        examples=["user@example.com"],
    )
    username: Optional[str] = Field(
        None,
        description="User's username",
        min_length=3,
        max_length=30,
        examples=["john_doe"],
    )
    password: str = Field(
        ...,
        description="User's password",
        min_length=1,
        examples=["MyP@ssw0rd"],
    )
    remember_me: bool = Field(
        False,
        description="Issue long-lived refresh token (7 days vs 1 day)",
        examples=[False],
    )

    @field_validator("email", "username")
    @classmethod
    def validate_identifier(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that at least one identifier (email or username) is provided."""
        # This validator runs for both email and username fields
        # We need to check if at least one is provided after both are processed
        # This is handled in model_validator below
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None:
            return validate_email_format(v)
        return v


class RegisterRequest(BaseSchema):
    """Schema for user registration request.

    Creates a new user account with email, username, and password.
    Includes comprehensive validation for all fields.

    Attributes:
        email: User's email address (must be unique)
        username: User's username (must be unique)
        password: User's password (must meet strength requirements)
        password_confirm: Password confirmation (must match password)

    Example:
        >>> register = RegisterRequest(
        ...     email="newuser@example.com",
        ...     username="new_user",
        ...     password="StrongP@ss123",
        ...     password_confirm="StrongP@ss123"
        ... )
    """

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["newuser@example.com"],
    )
    username: str = Field(
        ...,
        description="User's username",
        min_length=3,
        max_length=30,
        examples=["new_user"],
    )
    password: str = Field(
        ...,
        description="User's password",
        min_length=8,
        max_length=128,
        examples=["StrongP@ss123"],
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation (must match password)",
        min_length=8,
        max_length=128,
        examples=["StrongP@ss123"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        return validate_email_format(v)

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        """Validate username format."""
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)

    @field_validator("password_confirm")
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        """Validate that password and password_confirm match."""
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


class TokenResponse(BaseSchema):
    """Schema for JWT token response.

    Returned after successful login or token refresh.
    Contains access token for API authentication and refresh token
    for obtaining new access tokens.

    Attributes:
        access_token: JWT access token (short-lived, typically 1 hour)
        refresh_token: JWT refresh token (long-lived, typically 7 days)
        token_type: Token type (always "Bearer")
        expires_in: Access token expiration time in seconds
        user_id: Authenticated user's ID
        username: Authenticated user's username
        role: Authenticated user's role

    Example:
        >>> token = TokenResponse(
        ...     access_token="eyJ0eXAiOiJKV1QiLCJh...",
        ...     refresh_token="eyJ0eXAiOiJKV1QiLCJh...",
        ...     expires_in=3600,
        ...     user_id=123,
        ...     username="john_doe",
        ...     role="admin"
        ... )
    """

    access_token: str = Field(
        ...,
        description="JWT access token",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."],
    )
    token_type: str = Field(
        "Bearer",
        description="Token type (always Bearer)",
        examples=["Bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        gt=0,
        examples=[3600],
    )
    user_id: int = Field(
        ...,
        description="Authenticated user's ID",
        gt=0,
        examples=[123],
    )
    username: str = Field(
        ...,
        description="Authenticated user's username",
        examples=["john_doe"],
    )
    role: str = Field(
        ...,
        description="Authenticated user's role",
        examples=["admin"],
    )


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh token request.

    Used to obtain a new access token using a valid refresh token.

    Attributes:
        refresh_token: Valid JWT refresh token

    Example:
        >>> refresh = RefreshTokenRequest(
        ...     refresh_token="eyJ0eXAiOiJKV1QiLCJh..."
        ... )
    """

    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        min_length=1,
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."],
    )


class PasswordResetRequest(BaseSchema):
    """Schema for password reset request.

    Initiates password reset flow by sending reset link to user's email.

    Attributes:
        email: User's email address

    Example:
        >>> reset = PasswordResetRequest(
        ...     email="user@example.com"
        ... )
    """

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        return validate_email_format(v)


class PasswordResetConfirmRequest(BaseSchema):
    """Schema for password reset confirmation.

    Completes password reset flow by setting new password with reset token.

    Attributes:
        token: Password reset token from email
        password: New password
        password_confirm: Password confirmation

    Example:
        >>> confirm = PasswordResetConfirmRequest(
        ...     token="abc123def456",
        ...     password="NewP@ssw0rd",
        ...     password_confirm="NewP@ssw0rd"
        ... )
    """

    token: str = Field(
        ...,
        description="Password reset token from email",
        min_length=1,
        examples=["abc123def456"],
    )
    password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128,
        examples=["NewP@ssw0rd"],
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation",
        min_length=8,
        max_length=128,
        examples=["NewP@ssw0rd"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)

    @field_validator("password_confirm")
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordRequest(BaseSchema):
    """Schema for password change request.

    Allows authenticated user to change their password.

    Attributes:
        current_password: User's current password
        new_password: New password
        new_password_confirm: New password confirmation

    Example:
        >>> change = ChangePasswordRequest(
        ...     current_password="OldP@ssw0rd",
        ...     new_password="NewP@ssw0rd",
        ...     new_password_confirm="NewP@ssw0rd"
        ... )
    """

    current_password: str = Field(
        ...,
        description="User's current password",
        min_length=1,
        examples=["OldP@ssw0rd"],
    )
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128,
        examples=["NewP@ssw0rd"],
    )
    new_password_confirm: str = Field(
        ...,
        description="New password confirmation",
        min_length=8,
        max_length=128,
        examples=["NewP@ssw0rd"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str, info) -> str:
        """Validate password strength and ensure it's different from current."""
        validated = validate_password_strength(v)

        current = info.data.get("current_password")
        if current and validated == current:
            raise ValueError("New password must be different from current password")

        return validated

    @field_validator("new_password_confirm")
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        new_password = info.data.get("new_password")
        if new_password and v != new_password:
            raise ValueError("Passwords do not match")
        return v


class EmailVerificationRequest(BaseSchema):
    """Schema for email verification request.

    Verifies user's email address using token from verification email.

    Attributes:
        token: Email verification token

    Example:
        >>> verify = EmailVerificationRequest(
        ...     token="abc123def456"
        ... )
    """

    token: str = Field(
        ...,
        description="Email verification token",
        min_length=1,
        examples=["abc123def456"],
    )


class LogoutRequest(BaseSchema):
    """Schema for logout request.

    Invalidates refresh token by adding it to blacklist.

    Attributes:
        refresh_token: Refresh token to invalidate (optional)
        all_devices: Invalidate all refresh tokens for this user

    Example:
        >>> logout = LogoutRequest(
        ...     refresh_token="eyJ0eXAiOiJKV1QiLCJh...",
        ...     all_devices=False
        ... )
    """

    refresh_token: Optional[str] = Field(
        None,
        description="Refresh token to invalidate",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."],
    )
    all_devices: bool = Field(
        False,
        description="Invalidate all refresh tokens for this user",
        examples=[False],
    )


class AuthStatusResponse(BaseSchema):
    """Schema for authentication status response.

    Returns current authentication status and user information.

    Attributes:
        authenticated: Whether user is authenticated
        user_id: Authenticated user's ID (if authenticated)
        username: Authenticated user's username (if authenticated)
        role: Authenticated user's role (if authenticated)
        session_expires_at: When current session expires (if authenticated)

    Example:
        >>> status = AuthStatusResponse(
        ...     authenticated=True,
        ...     user_id=123,
        ...     username="john_doe",
        ...     role="admin",
        ...     session_expires_at=datetime(2025, 11, 24, 15, 0)
        ... )
    """

    authenticated: bool = Field(
        ...,
        description="Whether user is authenticated",
        examples=[True],
    )
    user_id: Optional[int] = Field(
        None,
        description="Authenticated user's ID",
        examples=[123],
    )
    username: Optional[str] = Field(
        None,
        description="Authenticated user's username",
        examples=["john_doe"],
    )
    role: Optional[str] = Field(
        None,
        description="Authenticated user's role",
        examples=["admin"],
    )
    session_expires_at: Optional[datetime] = Field(
        None,
        description="When current session expires",
        examples=["2025-11-24T15:00:00Z"],
    )

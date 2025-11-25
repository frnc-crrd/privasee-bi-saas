"""
Authentication service for user login, registration, and token management.

This service handles:
- User registration with validation
- User authentication (login)
- JWT token creation and refresh
- Token revocation (logout)
- Password reset flows
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from flask import current_app
from app.models import User
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.core.jwt_handler import JWTHandler
from app.core.token_blacklist import token_blacklist
from app.exceptions.auth import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AuthenticationError,
)
from app.exceptions.validation import ValidationError


class AuthService(BaseService[User]):
    """
    Handles all authentication-related business logic.

    This service manages user authentication, registration, and token
    lifecycle management.
    """

    def __init__(self) -> None:
        """Initialize AuthService with UserRepository."""
        super().__init__(UserRepository())
        self.user_repo = self.repository

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = 'viewer'
    ) -> Dict[str, Any]:
        """
        Register a new user with validation.

        Args:
            username: Desired username (3-50 chars)
            email: User email address
            password: Plain text password (will be hashed)
            role: User role (default: 'viewer')

        Returns:
            Dictionary with user data and tokens

        Raises:
            UserAlreadyExistsError: If email or username already exists
            ValidationError: If input validation fails

        Example:
            >>> auth_service = AuthService()
            >>> result = auth_service.register_user(
            ...     username="johndoe",
            ...     email="john@example.com",
            ...     password="SecurePass123!",
            ...     role="viewer"
            ... )
        """
        # Validate inputs
        self._validate_registration_data(username, email, password, role)

        # Check if user already exists
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsError(f"User with email {email} already exists")

        if self.user_repo.get_by_username(username):
            raise UserAlreadyExistsError(f"Username {username} is already taken")

        # Create new user
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        user.is_active = True

        # Save to database
        created_user = self.create(user)

        # Log registration
        self.log_action('user_registered', {
            'user_id': created_user.id,
            'username': username,
            'email': email,
            'role': role
        })

        # Generate tokens
        tokens = JWTHandler.create_tokens(
            user_id=created_user.id,
            additional_claims={'role': created_user.role, 'username': created_user.username}
        )

        return {
            'user': {
                'id': created_user.id,
                'username': created_user.username,
                'email': created_user.email,
                'role': created_user.role,
                'created_at': created_user.created_at.isoformat() if created_user.created_at else None
            },
            'tokens': tokens
        }

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with email and password.

        Args:
            email: User email address
            password: Plain text password

        Returns:
            Dictionary with user data and tokens

        Raises:
            InvalidCredentialsError: If credentials are invalid or account inactive

        Example:
            >>> auth_service = AuthService()
            >>> result = auth_service.authenticate_user(
            ...     email="john@example.com",
            ...     password="SecurePass123!"
            ... )
        """
        # Find user by email
        user = self.user_repo.get_by_email(email)

        if not user or not user.check_password(password):
            self.log_action('login_failed', {'email': email, 'reason': 'invalid_credentials'})
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            self.log_action('login_failed', {'email': email, 'reason': 'account_inactive'})
            raise InvalidCredentialsError("Account is disabled. Please contact support.")

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        self.update(user)

        # Log successful login
        self.log_action('login_success', {
            'user_id': user.id,
            'username': user.username,
            'email': email
        })

        # Generate tokens
        tokens = JWTHandler.create_tokens(
            user_id=user.id,
            additional_claims={'role': user.role, 'username': user.username}
        )

        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'last_login': user.last_login.isoformat() if user.last_login else None
            },
            'tokens': tokens
        }

    def refresh_access_token(self, refresh_token_claims: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token_claims: Claims from validated refresh token

        Returns:
            Dictionary with new access token

        Raises:
            AuthenticationError: If refresh token is invalid or user not found

        Example:
            >>> # In a protected route with refresh token
            >>> claims = get_jwt()
            >>> result = auth_service.refresh_access_token(claims)
        """
        user_id = refresh_token_claims.get('sub')
        if not user_id:
            raise AuthenticationError("Invalid refresh token: missing subject")

        # Verify user still exists and is active
        user = self.get_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        # Create new access token
        new_access_token = JWTHandler.create_access_token_from_refresh(refresh_token_claims)

        self.log_action('token_refreshed', {'user_id': user.id})

        return {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': int(JWTHandler.ACCESS_TOKEN_EXPIRES.total_seconds())
        }

    def logout_user(self, jti: str, token_expiry: datetime) -> None:
        """
        Logout user by blacklisting their token.

        Args:
            jti: JWT ID from token claims
            token_expiry: Token expiration datetime

        Example:
            >>> # In logout route
            >>> claims = get_jwt()
            >>> jti = claims['jti']
            >>> exp = datetime.fromtimestamp(claims['exp'], tz=timezone.utc)
            >>> auth_service.logout_user(jti, exp)
        """
        # Add token to blacklist
        token_blacklist.add_token(jti, token_expiry)

        user_id = JWTHandler.get_current_user_id()
        self.log_action('logout', {'user_id': user_id, 'jti': jti})

    def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        """
        Change user password with validation.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Raises:
            InvalidCredentialsError: If old password is incorrect
            ValidationError: If new password doesn't meet requirements

        Example:
            >>> auth_service.change_password(
            ...     user_id=1,
            ...     old_password="OldPass123!",
            ...     new_password="NewPass456!"
            ... )
        """
        user = self.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Verify old password
        if not user.check_password(old_password):
            raise InvalidCredentialsError("Current password is incorrect")

        # Validate new password
        self._validate_password(new_password)

        # Set new password
        user.set_password(new_password)
        self.update(user)

        self.log_action('password_changed', {'user_id': user_id})

    def _validate_registration_data(
        self,
        username: str,
        email: str,
        password: str,
        role: str
    ) -> None:
        """
        Validate user registration data.

        Args:
            username: Username to validate
            email: Email to validate
            password: Password to validate
            role: Role to validate

        Raises:
            ValidationError: If any validation fails
        """
        # Validate username
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        if len(username) > 50:
            raise ValidationError("Username must not exceed 50 characters")

        # Validate email
        if not email or '@' not in email:
            raise ValidationError("Invalid email address")

        # Validate password
        self._validate_password(password)

        # Validate role
        valid_roles = ['admin', 'analyst', 'viewer']
        if role not in valid_roles:
            raise ValidationError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    def _validate_password(self, password: str) -> None:
        """
        Validate password meets security requirements.

        Password requirements:
        - At least 8 characters
        - Contains uppercase letter
        - Contains lowercase letter
        - Contains digit
        - Contains special character

        Args:
            password: Password to validate

        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if not password or len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in password):
            raise ValidationError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            raise ValidationError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain at least one digit")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            raise ValidationError("Password must contain at least one special character")

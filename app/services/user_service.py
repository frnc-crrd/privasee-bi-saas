"""
User management service for CRUD operations and profile management.

This service handles:
- User profile retrieval and updates
- User listing with pagination and filtering
- User soft deletion (deactivation)
- User search and statistics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from flask import current_app
from app.models import User
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.exceptions.auth import InsufficientPermissionsError, AuthorizationError
from app.exceptions.validation import ValidationError
from app.exceptions.base import ResourceNotFoundError


class UserService(BaseService[User]):
    """
    Handles user management business logic.

    This service provides user CRUD operations, profile management,
    and user administration features.
    """

    def __init__(self) -> None:
        """Initialize UserService with UserRepository."""
        super().__init__(UserRepository())
        self.user_repo = self.repository

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Get user profile by ID.

        Args:
            user_id: User ID

        Returns:
            Dictionary with user profile data

        Raises:
            ResourceNotFoundError: If user not found

        Example:
            >>> user_service = UserService()
            >>> profile = user_service.get_user_profile(user_id=1)
        """
        user = self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User with ID {user_id} not found")

        return self._user_to_dict(user)

    def update_user_profile(
        self,
        user_id: int,
        current_user_id: int,
        current_user_role: str,
        **update_data: Any
    ) -> Dict[str, Any]:
        """
        Update user profile with authorization checks.

        Users can update their own profile. Admins can update any user.

        Args:
            user_id: ID of user to update
            current_user_id: ID of user making the request
            current_user_role: Role of user making the request
            **update_data: Fields to update (username, email, role, is_active)

        Returns:
            Updated user profile dictionary

        Raises:
            ResourceNotFoundError: If user not found
            AuthorizationError: If user not authorized to update
            ValidationError: If update data is invalid

        Example:
            >>> user_service.update_user_profile(
            ...     user_id=1,
            ...     current_user_id=1,
            ...     current_user_role="viewer",
            ...     username="new_username"
            ... )
        """
        # Get user to update
        user = self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User with ID {user_id} not found")

        # Authorization check: users can update themselves, admins can update anyone
        if current_user_id != user_id and current_user_role != 'admin':
            raise AuthorizationError("You can only update your own profile")

        # Validate and apply updates
        allowed_fields = ['username', 'email']

        # Only admins can change role and is_active
        if current_user_role == 'admin':
            allowed_fields.extend(['role', 'is_active'])

        for field, value in update_data.items():
            if field not in allowed_fields:
                raise ValidationError(f"Field '{field}' cannot be updated")

            if field == 'username':
                self._validate_username_update(user_id, value)
            elif field == 'email':
                self._validate_email_update(user_id, value)
            elif field == 'role':
                self._validate_role(value)

            setattr(user, field, value)

        # Update user
        updated_user = self.update(user)

        self.log_action('user_updated', {
            'user_id': user_id,
            'updated_by': current_user_id,
            'fields': list(update_data.keys())
        })

        return self._user_to_dict(updated_user)

    def list_users(
        self,
        current_user_role: str,
        skip: int = 0,
        limit: int = 100,
        role_filter: Optional[str] = None,
        is_active_filter: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List users with pagination and filtering.

        Only admins and analysts can list users.

        Args:
            current_user_role: Role of user making request
            skip: Number of records to skip (for pagination)
            limit: Maximum records to return
            role_filter: Filter by user role
            is_active_filter: Filter by active status
            search_query: Search in username/email

        Returns:
            Dictionary with users list and pagination metadata

        Raises:
            InsufficientPermissionsError: If user lacks permission

        Example:
            >>> users = user_service.list_users(
            ...     current_user_role="admin",
            ...     skip=0,
            ...     limit=50,
            ...     role_filter="viewer"
            ... )
        """
        # Authorization check
        if current_user_role not in ['admin', 'analyst']:
            raise InsufficientPermissionsError(
                "Only admins and analysts can list users"
            )

        # Apply filters
        filters = {}
        if role_filter:
            filters['role'] = role_filter
        if is_active_filter is not None:
            filters['is_active'] = is_active_filter

        # Get users with filters
        if search_query:
            users = self.user_repo.search_users(search_query, skip=skip, limit=limit)
        elif filters:
            users = self.user_repo.filter_users(filters, skip=skip, limit=limit)
        else:
            users = self.get_all(skip=skip, limit=limit)

        # Get total count for pagination
        total_count = self.user_repo.count(filters=filters if filters else None)

        return {
            'users': [self._user_to_dict(user) for user in users],
            'pagination': {
                'total': total_count,
                'skip': skip,
                'limit': limit,
                'has_more': (skip + limit) < total_count
            }
        }

    def deactivate_user(
        self,
        user_id: int,
        current_user_id: int,
        current_user_role: str
    ) -> Dict[str, Any]:
        """
        Soft delete user by deactivating account.

        Only admins can deactivate users. Users cannot deactivate themselves.

        Args:
            user_id: ID of user to deactivate
            current_user_id: ID of user making request
            current_user_role: Role of user making request

        Returns:
            Dictionary with deactivation confirmation

        Raises:
            InsufficientPermissionsError: If not admin
            ResourceNotFoundError: If user not found
            ValidationError: If trying to deactivate self

        Example:
            >>> result = user_service.deactivate_user(
            ...     user_id=5,
            ...     current_user_id=1,
            ...     current_user_role="admin"
            ... )
        """
        # Authorization check
        if current_user_role != 'admin':
            raise InsufficientPermissionsError("Only admins can deactivate users")

        if user_id == current_user_id:
            raise ValidationError("You cannot deactivate your own account")

        # Get user
        user = self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User with ID {user_id} not found")

        # Deactivate user
        user.is_active = False
        updated_user = self.update(user)

        self.log_action('user_deactivated', {
            'user_id': user_id,
            'deactivated_by': current_user_id
        })

        return {
            'message': f'User {user.username} has been deactivated',
            'user_id': user_id,
            'is_active': False
        }

    def activate_user(
        self,
        user_id: int,
        current_user_role: str
    ) -> Dict[str, Any]:
        """
        Reactivate a deactivated user account.

        Only admins can activate users.

        Args:
            user_id: ID of user to activate
            current_user_role: Role of user making request

        Returns:
            Dictionary with activation confirmation

        Raises:
            InsufficientPermissionsError: If not admin
            ResourceNotFoundError: If user not found

        Example:
            >>> result = user_service.activate_user(
            ...     user_id=5,
            ...     current_user_role="admin"
            ... )
        """
        # Authorization check
        if current_user_role != 'admin':
            raise InsufficientPermissionsError("Only admins can activate users")

        # Get user
        user = self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User with ID {user_id} not found")

        # Activate user
        user.is_active = True
        updated_user = self.update(user)

        self.log_action('user_activated', {'user_id': user_id})

        return {
            'message': f'User {user.username} has been activated',
            'user_id': user_id,
            'is_active': True
        }

    def get_user_statistics(self, current_user_role: str) -> Dict[str, Any]:
        """
        Get user statistics (total, by role, active/inactive).

        Only admins and analysts can view statistics.

        Args:
            current_user_role: Role of user making request

        Returns:
            Dictionary with user statistics

        Raises:
            InsufficientPermissionsError: If user lacks permission

        Example:
            >>> stats = user_service.get_user_statistics(current_user_role="admin")
        """
        # Authorization check
        if current_user_role not in ['admin', 'analyst']:
            raise InsufficientPermissionsError(
                "Only admins and analysts can view statistics"
            )

        return self.user_repo.get_user_statistics()

    def _user_to_dict(self, user: User, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert User model to dictionary.

        Args:
            user: User model instance
            include_sensitive: Whether to include sensitive fields

        Returns:
            User dictionary
        """
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }

        return user_dict

    def _validate_username_update(self, user_id: int, username: str) -> None:
        """
        Validate username update (uniqueness, format).

        Args:
            user_id: ID of user being updated
            username: New username

        Raises:
            ValidationError: If validation fails
        """
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")

        if len(username) > 50:
            raise ValidationError("Username must not exceed 50 characters")

        # Check uniqueness (excluding current user)
        existing_user = self.user_repo.get_by_username(username)
        if existing_user and existing_user.id != user_id:
            raise ValidationError(f"Username {username} is already taken")

    def _validate_email_update(self, user_id: int, email: str) -> None:
        """
        Validate email update (uniqueness, format).

        Args:
            user_id: ID of user being updated
            email: New email

        Raises:
            ValidationError: If validation fails
        """
        if not email or '@' not in email:
            raise ValidationError("Invalid email address")

        # Check uniqueness (excluding current user)
        existing_user = self.user_repo.get_by_email(email)
        if existing_user and existing_user.id != user_id:
            raise ValidationError(f"Email {email} is already registered")

    def _validate_role(self, role: str) -> None:
        """
        Validate role value.

        Args:
            role: Role to validate

        Raises:
            ValidationError: If role is invalid
        """
        valid_roles = ['admin', 'analyst', 'viewer']
        if role not in valid_roles:
            raise ValidationError(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )

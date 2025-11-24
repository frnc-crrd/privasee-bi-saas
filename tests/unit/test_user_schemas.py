"""Unit tests for app.schemas.user_schemas module.

Tests all user management schemas.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.user_schemas import (
    UserCreateRequest,
    UserFilterParams,
    UserListItemResponse,
    UserProfileUpdateRequest,
    UserResponse,
    UserStatsResponse,
    UserUpdateRequest,
)


class TestUserResponse:
    """Test UserResponse schema."""

    def test_valid_user_response(self):
        """Test valid user response."""
        data = {
            "id": 123,
            "username": "john_doe",
            "email": "john@example.com",
            "role": "analyst",
            "is_active": True,
            "last_login": datetime(2025, 11, 24, 10, 0),
            "created_at": datetime(2025, 11, 1, 9, 0),
            "updated_at": datetime(2025, 11, 24, 10, 0),
        }
        user = UserResponse(**data)
        assert user.id == 123
        assert user.username == "john_doe"
        assert user.email == "john@example.com"
        assert user.role == "analyst"
        assert user.is_active is True

    def test_user_response_missing_required_field(self):
        """Test that missing required fields fail."""
        data = {
            "id": 123,
            "username": "john_doe",
            # Missing email
            "role": "analyst",
            "is_active": True,
            "created_at": datetime(2025, 11, 1, 9, 0),
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(**data)
        assert "email" in str(exc_info.value)

    def test_user_response_invalid_id(self):
        """Test that invalid ID fails."""
        data = {
            "id": 0,  # Must be > 0
            "username": "john_doe",
            "email": "john@example.com",
            "role": "analyst",
            "is_active": True,
            "created_at": datetime(2025, 11, 1, 9, 0),
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(**data)
        assert "id" in str(exc_info.value).lower()


class TestUserListItemResponse:
    """Test UserListItemResponse schema."""

    def test_valid_user_list_item(self):
        """Test valid user list item."""
        data = {
            "id": 123,
            "username": "john_doe",
            "email": "john@example.com",
            "role": "analyst",
            "is_active": True,
            "created_at": datetime(2025, 11, 1, 9, 0),
        }
        user = UserListItemResponse(**data)
        assert user.id == 123
        assert user.username == "john_doe"


class TestUserCreateRequest:
    """Test UserCreateRequest schema."""

    def test_valid_user_create(self):
        """Test valid user creation request."""
        data = {
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "TempP@ss123",
            "role": "viewer",
            "is_active": True,
        }
        user = UserCreateRequest(**data)
        assert user.username == "new_user"
        assert user.email == "newuser@example.com"
        assert user.role == "viewer"
        assert user.is_active is True

    def test_user_create_default_role(self):
        """Test that default role is 'viewer'."""
        data = {
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "TempP@ss123",
        }
        user = UserCreateRequest(**data)
        assert user.role == "viewer"

    def test_user_create_default_is_active(self):
        """Test that default is_active is True."""
        data = {
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "TempP@ss123",
        }
        user = UserCreateRequest(**data)
        assert user.is_active is True

    def test_user_create_invalid_username(self):
        """Test that invalid username fails."""
        data = {
            "username": "ab",  # Too short
            "email": "newuser@example.com",
            "password": "TempP@ss123",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreateRequest(**data)
        assert "username" in str(exc_info.value).lower()

    def test_user_create_invalid_email(self):
        """Test that invalid email fails."""
        data = {
            "username": "new_user",
            "email": "invalid-email",
            "password": "TempP@ss123",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreateRequest(**data)
        assert "email" in str(exc_info.value).lower()

    def test_user_create_invalid_role(self):
        """Test that invalid role fails."""
        data = {
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "TempP@ss123",
            "role": "superuser",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreateRequest(**data)
        assert "role" in str(exc_info.value).lower()


class TestUserUpdateRequest:
    """Test UserUpdateRequest schema."""

    def test_user_update_all_fields(self):
        """Test updating all fields."""
        data = {
            "username": "updated_username",
            "email": "newemail@example.com",
            "role": "admin",
            "is_active": False,
        }
        update = UserUpdateRequest(**data)
        assert update.username == "updated_username"
        assert update.email == "newemail@example.com"
        assert update.role == "admin"
        assert update.is_active is False

    def test_user_update_partial_fields(self):
        """Test updating only some fields."""
        data = {
            "role": "admin",
        }
        update = UserUpdateRequest(**data)
        assert update.role == "admin"
        assert update.username is None
        assert update.email is None
        assert update.is_active is None

    def test_user_update_empty(self):
        """Test that empty update is valid."""
        update = UserUpdateRequest(**{})
        assert update.username is None
        assert update.email is None
        assert update.role is None
        assert update.is_active is None

    def test_user_update_invalid_username(self):
        """Test that invalid username fails."""
        data = {"username": "ab"}  # Too short
        with pytest.raises(ValidationError) as exc_info:
            UserUpdateRequest(**data)
        assert "username" in str(exc_info.value).lower()

    def test_user_update_invalid_role(self):
        """Test that invalid role fails."""
        data = {"role": "superuser"}
        with pytest.raises(ValidationError) as exc_info:
            UserUpdateRequest(**data)
        assert "role" in str(exc_info.value).lower()


class TestUserProfileUpdateRequest:
    """Test UserProfileUpdateRequest schema."""

    def test_profile_update_username(self):
        """Test updating username."""
        data = {"username": "new_username"}
        update = UserProfileUpdateRequest(**data)
        assert update.username == "new_username"

    def test_profile_update_email(self):
        """Test updating email."""
        data = {"email": "newemail@example.com"}
        update = UserProfileUpdateRequest(**data)
        assert update.email == "newemail@example.com"

    def test_profile_update_both_fields(self):
        """Test updating both fields."""
        data = {
            "username": "new_username",
            "email": "newemail@example.com",
        }
        update = UserProfileUpdateRequest(**data)
        assert update.username == "new_username"
        assert update.email == "newemail@example.com"

    def test_profile_update_empty(self):
        """Test that empty update is valid."""
        update = UserProfileUpdateRequest(**{})
        assert update.username is None
        assert update.email is None

    def test_profile_update_invalid_username(self):
        """Test that invalid username fails."""
        data = {"username": "ab"}  # Too short
        with pytest.raises(ValidationError) as exc_info:
            UserProfileUpdateRequest(**data)
        assert "username" in str(exc_info.value).lower()


class TestUserFilterParams:
    """Test UserFilterParams schema."""

    def test_filter_by_role(self):
        """Test filtering by role."""
        data = {"role": "analyst"}
        filters = UserFilterParams(**data)
        assert filters.role == "analyst"

    def test_filter_by_is_active(self):
        """Test filtering by active status."""
        data = {"is_active": True}
        filters = UserFilterParams(**data)
        assert filters.is_active is True

    def test_filter_by_search(self):
        """Test filtering by search term."""
        data = {"search": "john"}
        filters = UserFilterParams(**data)
        assert filters.search == "john"

    def test_filter_by_dates(self):
        """Test filtering by date range."""
        data = {
            "created_after": datetime(2025, 1, 1),
            "created_before": datetime(2025, 12, 31),
        }
        filters = UserFilterParams(**data)
        assert filters.created_after == datetime(2025, 1, 1)
        assert filters.created_before == datetime(2025, 12, 31)

    def test_filter_all_params(self):
        """Test all filter parameters."""
        data = {
            "role": "analyst",
            "is_active": True,
            "search": "john",
            "created_after": datetime(2025, 1, 1),
            "created_before": datetime(2025, 12, 31),
        }
        filters = UserFilterParams(**data)
        assert filters.role == "analyst"
        assert filters.is_active is True
        assert filters.search == "john"

    def test_filter_empty(self):
        """Test empty filter parameters."""
        filters = UserFilterParams(**{})
        assert filters.role is None
        assert filters.is_active is None
        assert filters.search is None

    def test_filter_invalid_role(self):
        """Test that invalid role fails."""
        data = {"role": "superuser"}
        with pytest.raises(ValidationError) as exc_info:
            UserFilterParams(**data)
        assert "role" in str(exc_info.value).lower()


class TestUserStatsResponse:
    """Test UserStatsResponse schema."""

    def test_valid_user_stats(self):
        """Test valid user statistics."""
        data = {
            "total_users": 100,
            "active_users": 85,
            "inactive_users": 15,
            "users_by_role": {
                "admin": 5,
                "analyst": 30,
                "viewer": 65,
            },
            "recent_registrations": 12,
        }
        stats = UserStatsResponse(**data)
        assert stats.total_users == 100
        assert stats.active_users == 85
        assert stats.inactive_users == 15
        assert stats.users_by_role["admin"] == 5
        assert stats.recent_registrations == 12

    def test_user_stats_missing_field(self):
        """Test that missing required fields fail."""
        data = {
            "total_users": 100,
            "active_users": 85,
            # Missing inactive_users
            "users_by_role": {"admin": 5},
            "recent_registrations": 12,
        }
        with pytest.raises(ValidationError) as exc_info:
            UserStatsResponse(**data)
        assert "inactive_users" in str(exc_info.value)

    def test_user_stats_negative_values(self):
        """Test that negative values fail."""
        data = {
            "total_users": -1,
            "active_users": 85,
            "inactive_users": 15,
            "users_by_role": {"admin": 5},
            "recent_registrations": 12,
        }
        with pytest.raises(ValidationError) as exc_info:
            UserStatsResponse(**data)
        assert "total_users" in str(exc_info.value).lower()

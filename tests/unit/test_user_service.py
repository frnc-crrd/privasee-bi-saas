"""
Unit tests for user management service module.

This module contains comprehensive tests for user CRUD operations,
profile management, and user administration features.

Test Coverage:
    - User profile retrieval
    - User profile updates with authorization
    - User listing with pagination and filtering
    - User activation and deactivation
    - User statistics
    - Field validation (username, email, role)
    - Authorization and permission checks

Business Value:
    - Secure user management
    - Role-based access control
    - Profile integrity
"""

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

import pytest

from app.services.user_service import UserService
from app.models import User
from app.exceptions.auth import InsufficientPermissionsError, AuthorizationError
from app.exceptions.validation import ValidationError
from app.exceptions.base import ResourceNotFoundError


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = 1
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.role = 'viewer'
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    user.last_login = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    return user


class TestGetUserProfile:
    """Tests for user profile retrieval."""

    @patch('app.services.user_service.UserRepository')
    def test_get_user_profile_success(self, mock_repo_class, mock_user):
        """Test successful user profile retrieval.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - User profile returned as dictionary
            - All fields present
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.get_user_profile(user_id=1)

        # Assert
        assert result['id'] == 1
        assert result['username'] == 'testuser'
        assert result['email'] == 'test@example.com'
        assert result['role'] == 'viewer'
        assert result['is_active'] is True

    @patch('app.services.user_service.UserRepository')
    def test_get_user_profile_not_found(self, mock_repo_class):
        """Test profile retrieval when user does not exist.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - ResourceNotFoundError raised
            - Error message includes user ID
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = None
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            service.get_user_profile(user_id=999)

        assert '999' in str(exc_info.value)


class TestUpdateUserProfile:
    """Tests for user profile updates with authorization."""

    @patch('app.services.user_service.UserRepository')
    def test_update_own_profile_success(self, mock_repo_class, mock_user):
        """Test user updating their own profile.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - User can update their own profile
            - Allowed fields updated
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo.get_by_username.return_value = None

        # Update the mock_user to reflect the new username
        def update_side_effect(user):
            user.username = 'newusername'
            return user

        mock_repo.update.side_effect = update_side_effect
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.update_user_profile(
            user_id=1,
            current_user_id=1,
            current_user_role='viewer',
            username='newusername'
        )

        # Assert
        assert result['username'] == 'newusername'
        mock_repo.update.assert_called_once()

    @patch('app.services.user_service.UserRepository')
    def test_update_other_user_as_non_admin_fails(self, mock_repo_class, mock_user):
        """Test non-admin cannot update other users.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - AuthorizationError raised
            - Update not executed
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            service.update_user_profile(
                user_id=1,
                current_user_id=2,
                current_user_role='viewer',
                username='newname'
            )

        assert 'own profile' in str(exc_info.value)
        mock_repo.update.assert_not_called()

    @patch('app.services.user_service.UserRepository')
    def test_admin_can_update_any_user(self, mock_repo_class, mock_user):
        """Test admin can update any user profile.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - Admin can update other users
            - Role and is_active fields allowed for admin
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo.get_by_email.return_value = None
        mock_repo.update.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.update_user_profile(
            user_id=1,
            current_user_id=2,
            current_user_role='admin',
            email='newemail@example.com',
            role='analyst',
            is_active=False
        )

        # Assert
        mock_repo.update.assert_called_once()

    @patch('app.services.user_service.UserRepository')
    def test_update_disallowed_field_fails(self, mock_repo_class, mock_user):
        """Test updating disallowed field raises error.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - ValidationError for disallowed fields
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.update_user_profile(
                user_id=1,
                current_user_id=1,
                current_user_role='viewer',
                password='newpassword'  # Not allowed
            )

        assert 'cannot be updated' in str(exc_info.value)

    @patch('app.services.user_service.UserRepository')
    def test_non_admin_cannot_update_role(self, mock_repo_class, mock_user):
        """Test non-admin cannot update role field.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - ValidationError when non-admin tries to update role
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError):
            service.update_user_profile(
                user_id=1,
                current_user_id=1,
                current_user_role='viewer',
                role='admin'
            )

    @patch('app.services.user_service.UserRepository')
    def test_update_username_duplicate_fails(self, mock_repo_class, mock_user):
        """Test updating to duplicate username fails.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - ValidationError for duplicate username
        """
        # Arrange
        existing_user = Mock(spec=User)
        existing_user.id = 2
        existing_user.username = 'existing'

        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo.get_by_username.return_value = existing_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.update_user_profile(
                user_id=1,
                current_user_id=1,
                current_user_role='viewer',
                username='existing'
            )

        assert 'already taken' in str(exc_info.value)

    @patch('app.services.user_service.UserRepository')
    def test_update_email_duplicate_fails(self, mock_repo_class, mock_user):
        """Test updating to duplicate email fails.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - ValidationError for duplicate email
        """
        # Arrange
        existing_user = Mock(spec=User)
        existing_user.id = 2
        existing_user.email = 'existing@example.com'

        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo.get_by_email.return_value = existing_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.update_user_profile(
                user_id=1,
                current_user_id=1,
                current_user_role='viewer',
                email='existing@example.com'
            )

        assert 'already registered' in str(exc_info.value)

    @patch('app.services.user_service.UserRepository')
    def test_update_invalid_role_fails(self, mock_repo_class, mock_user):
        """Test updating to invalid role fails.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - ValidationError for invalid role
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.update_user_profile(
                user_id=1,
                current_user_id=1,
                current_user_role='admin',
                role='superuser'  # Invalid role
            )

        assert 'Invalid role' in str(exc_info.value)


class TestListUsers:
    """Tests for user listing with pagination and filtering."""

    @patch('app.services.user_service.UserRepository')
    def test_list_users_as_admin(self, mock_repo_class, mock_user):
        """Test admin can list users.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - Users list returned with pagination metadata
            - Total count included
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_all.return_value = [mock_user]
        mock_repo.count.return_value = 1
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.list_users(current_user_role='admin')

        # Assert
        assert len(result['users']) == 1
        assert result['pagination']['total'] == 1
        assert 'has_more' in result['pagination']

    @patch('app.services.user_service.UserRepository')
    def test_list_users_as_analyst(self, mock_repo_class, mock_user):
        """Test analyst can list users.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - Analysts have permission to list users
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_all.return_value = [mock_user]
        mock_repo.count.return_value = 1
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.list_users(current_user_role='analyst')

        # Assert
        assert len(result['users']) == 1

    @patch('app.services.user_service.UserRepository')
    def test_list_users_as_viewer_fails(self, mock_repo_class):
        """Test viewer cannot list users.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - InsufficientPermissionsError raised
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(InsufficientPermissionsError) as exc_info:
            service.list_users(current_user_role='viewer')

        assert 'admins and analysts' in str(exc_info.value).lower()

    @patch('app.services.user_service.UserRepository')
    def test_list_users_with_role_filter(self, mock_repo_class, mock_user):
        """Test listing users with role filter.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - Filter applied correctly
            - Repository filter_users called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.filter_users.return_value = [mock_user]
        mock_repo.count.return_value = 1
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.list_users(
            current_user_role='admin',
            role_filter='admin'
        )

        # Assert
        mock_repo.filter_users.assert_called_once()
        call_filters = mock_repo.filter_users.call_args[0][0]
        assert call_filters['role'] == 'admin'

    @patch('app.services.user_service.UserRepository')
    def test_list_users_with_search_query(self, mock_repo_class, mock_user):
        """Test listing users with search query.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - Search query applied
            - Repository search_users called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.search_users.return_value = [mock_user]
        mock_repo.count.return_value = 1
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.list_users(
            current_user_role='admin',
            search_query='john'
        )

        # Assert
        mock_repo.search_users.assert_called_once()
        assert 'john' in mock_repo.search_users.call_args[0][0]


class TestDeactivateUser:
    """Tests for user deactivation (soft delete)."""

    @patch('app.services.user_service.UserRepository')
    def test_admin_can_deactivate_user(self, mock_repo_class, mock_user):
        """Test admin can deactivate users.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - User deactivated successfully
            - is_active set to False
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo.update.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.deactivate_user(
            user_id=1,
            current_user_id=2,
            current_user_role='admin'
        )

        # Assert
        assert result['is_active'] is False
        assert 'deactivated' in result['message'].lower()

    @patch('app.services.user_service.UserRepository')
    def test_non_admin_cannot_deactivate_user(self, mock_repo_class):
        """Test non-admin cannot deactivate users.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - InsufficientPermissionsError raised
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(InsufficientPermissionsError):
            service.deactivate_user(
                user_id=1,
                current_user_id=2,
                current_user_role='viewer'
            )

    @patch('app.services.user_service.UserRepository')
    def test_cannot_deactivate_self(self, mock_repo_class):
        """Test user cannot deactivate their own account.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - ValidationError raised
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.deactivate_user(
                user_id=1,
                current_user_id=1,
                current_user_role='admin'
            )

        assert 'own account' in str(exc_info.value)


class TestActivateUser:
    """Tests for user activation."""

    @patch('app.services.user_service.UserRepository')
    def test_admin_can_activate_user(self, mock_repo_class, mock_user):
        """Test admin can activate users.

        Args:
            mock_repo_class: Mocked repository class
            mock_user: Mock user fixture

        Assertions:
            - User activated successfully
            - is_active set to True
        """
        # Arrange
        mock_user.is_active = False
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = mock_user
        mock_repo.update.return_value = mock_user
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.activate_user(
            user_id=1,
            current_user_role='admin'
        )

        # Assert
        assert result['is_active'] is True
        assert 'activated' in result['message'].lower()

    @patch('app.services.user_service.UserRepository')
    def test_non_admin_cannot_activate_user(self, mock_repo_class):
        """Test non-admin cannot activate users.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - InsufficientPermissionsError raised
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(InsufficientPermissionsError):
            service.activate_user(
                user_id=1,
                current_user_role='viewer'
            )


class TestGetUserStatistics:
    """Tests for user statistics retrieval."""

    @patch('app.services.user_service.UserRepository')
    def test_admin_can_get_statistics(self, mock_repo_class):
        """Test admin can retrieve user statistics.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - Statistics returned
            - Repository method called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_user_statistics.return_value = {
            'total_users': 100,
            'active_users': 85,
            'by_role': {'admin': 5, 'analyst': 20, 'viewer': 75}
        }
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.get_user_statistics(current_user_role='admin')

        # Assert
        assert result['total_users'] == 100
        assert result['active_users'] == 85
        mock_repo.get_user_statistics.assert_called_once()

    @patch('app.services.user_service.UserRepository')
    def test_analyst_can_get_statistics(self, mock_repo_class):
        """Test analyst can retrieve user statistics.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - Analysts have permission
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_user_statistics.return_value = {'total_users': 50}
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act
        result = service.get_user_statistics(current_user_role='analyst')

        # Assert
        assert 'total_users' in result

    @patch('app.services.user_service.UserRepository')
    def test_viewer_cannot_get_statistics(self, mock_repo_class):
        """Test viewer cannot retrieve user statistics.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - InsufficientPermissionsError raised
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(InsufficientPermissionsError):
            service.get_user_statistics(current_user_role='viewer')


class TestFieldValidation:
    """Tests for field validation helper methods."""

    @patch('app.services.user_service.UserRepository')
    def test_validate_username_too_short(self, mock_repo_class):
        """Test username validation for minimum length.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - ValidationError for short usernames
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service._validate_username_update(1, 'ab')

        assert '3 characters' in str(exc_info.value)

    @patch('app.services.user_service.UserRepository')
    def test_validate_username_too_long(self, mock_repo_class):
        """Test username validation for maximum length.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - ValidationError for long usernames
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service._validate_username_update(1, 'a' * 51)

        assert '50 characters' in str(exc_info.value)

    @patch('app.services.user_service.UserRepository')
    def test_validate_email_invalid_format(self, mock_repo_class):
        """Test email validation for format.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - ValidationError for invalid email format
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service._validate_email_update(1, 'notanemail')

        assert 'Invalid email' in str(exc_info.value)

    @patch('app.services.user_service.UserRepository')
    def test_validate_role_invalid(self, mock_repo_class):
        """Test role validation for valid values.

        Args:
            mock_repo_class: Mocked repository class

        Assertions:
            - ValidationError for invalid roles
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = UserService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service._validate_role('superuser')

        assert 'Invalid role' in str(exc_info.value)
        assert 'admin, analyst, viewer' in str(exc_info.value)

"""
Unit tests for RBAC middleware module.

This module contains comprehensive tests for role-based access control
decorators and permission checking.

Test Coverage:
    - Role requirement decorators
    - Multiple role authorization
    - Role hierarchy enforcement    - Resource ownership validation
    - Permission-based access control
    - Error handling for unauthorized access
    - Edge cases and missing data

Business Value:
    - Ensures security boundaries are enforced
    - Validates authorization logic
    - Prevents unauthorized access to protected resources
"""

from unittest.mock import patch, MagicMock

import pytest

from app.middleware.rbac_middleware import (
    require_role,
    require_any_role,
    require_admin,
    require_analyst_or_admin,
    require_minimum_role,
    check_resource_ownership,
    require_resource_ownership,
    get_user_permissions,
    has_permission,
    require_permission,
    ROLE_HIERARCHY,
)
from app.exceptions.auth import InsufficientPermissionsError, AuthorizationError


class TestRequireRoleDecorator:
    """Tests for require_role decorator."""

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_role_admin_allows_admin(self, mock_get_role):
        """Test admin role is allowed for admin-only route.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Function executes successfully for admin user
            - Return value is correct
        """
        mock_get_role.return_value = 'admin'

        @require_role('admin')
        def admin_only_route():
            return {'message': 'admin access'}

        result = admin_only_route()

        assert result == {'message': 'admin access'}
        mock_get_role.assert_called_once()

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_role_admin_denies_viewer(self, mock_get_role):
        """Test viewer role is denied for admin-only route.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - InsufficientPermissionsError raised
            - Error message mentions required role
        """
        mock_get_role.return_value = 'viewer'

        @require_role('admin')
        def admin_only_route():
            return {'message': 'admin access'}

        with pytest.raises(InsufficientPermissionsError) as exc_info:
            admin_only_route()

        assert 'admin' in str(exc_info.value)

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_role_multiple_roles_allows_any(self, mock_get_role):
        """Test multiple allowed roles grants access to any matching role.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Admin user can access
            - Analyst user can access
        """
        @require_role('admin', 'analyst')
        def analyst_or_admin_route():
            return {'message': 'access granted'}

        mock_get_role.return_value = 'admin'
        result = analyst_or_admin_route()
        assert result == {'message': 'access granted'}

        mock_get_role.return_value = 'analyst'
        result = analyst_or_admin_route()
        assert result == {'message': 'access granted'}

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_role_multiple_roles_denies_viewer(self, mock_get_role):
        """Test multiple allowed roles denies non-matching role.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Viewer is denied access
            - Error message lists required roles
        """
        mock_get_role.return_value = 'viewer'

        @require_role('admin', 'analyst')
        def analyst_or_admin_route():
            return {'message': 'access granted'}

        with pytest.raises(InsufficientPermissionsError) as exc_info:
            analyst_or_admin_route()

        error_msg = str(exc_info.value).lower()
        assert 'admin' in error_msg or 'analyst' in error_msg

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_role_missing_role_claim(self, mock_get_role):
        """Test error handling when user role is missing.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - AuthorizationError raised
            - Error message mentions authentication required
        """
        mock_get_role.return_value = None

        @require_role('admin')
        def admin_only_route():
            return {'message': 'admin access'}

        with pytest.raises(AuthorizationError) as exc_info:
            admin_only_route()

        assert 'authentication required' in str(exc_info.value).lower()

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_role_invalid_role(self, mock_get_role):
        """Test behavior with unknown role value.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Invalid role is denied access
        """
        mock_get_role.return_value = 'invalid_role'

        @require_role('admin')
        def admin_only_route():
            return {'message': 'admin access'}

        with pytest.raises(InsufficientPermissionsError):
            admin_only_route()


class TestRequireAnyRoleAlias:
    """Tests for require_any_role alias."""

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_any_role_is_alias(self, mock_get_role):
        """Test require_any_role behaves identically to require_role.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Function works same as require_role
        """
        mock_get_role.return_value = 'analyst'

        @require_any_role('admin', 'analyst', 'viewer')
        def all_users_route():
            return {'message': 'all users'}

        result = all_users_route()

        assert result == {'message': 'all users'}


class TestShorthandDecorators:
    """Tests for shorthand role decorators."""

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_admin_allows_admin(self, mock_get_role):
        """Test require_admin shorthand decorator.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Admin role grants access
        """
        mock_get_role.return_value = 'admin'

        @require_admin()
        def admin_route():
            return {'message': 'admin only'}

        result = admin_route()

        assert result == {'message': 'admin only'}

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_admin_denies_non_admin(self, mock_get_role):
        """Test require_admin denies non-admin users.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Analyst is denied
        """
        mock_get_role.return_value = 'analyst'

        @require_admin()
        def admin_route():
            return {'message': 'admin only'}

        with pytest.raises(InsufficientPermissionsError):
            admin_route()

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_analyst_or_admin_allows_both(self, mock_get_role):
        """Test require_analyst_or_admin allows analyst and admin.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Admin can access
            - Analyst can access
        """
        @require_analyst_or_admin()
        def analytics_route():
            return {'data': 'analytics'}

        mock_get_role.return_value = 'admin'
        result = analytics_route()
        assert result == {'data': 'analytics'}

        mock_get_role.return_value = 'analyst'
        result = analytics_route()
        assert result == {'data': 'analytics'}

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_analyst_or_admin_denies_viewer(self, mock_get_role):
        """Test require_analyst_or_admin denies viewer.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Viewer is denied access
        """
        mock_get_role.return_value = 'viewer'

        @require_analyst_or_admin()
        def analytics_route():
            return {'data': 'analytics'}

        with pytest.raises(InsufficientPermissionsError):
            analytics_route()


class TestMinimumRoleHierarchy:
    """Tests for role hierarchy enforcement."""

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_minimum_role_analyst_allows_admin(self, mock_get_role):
        """Test minimum role allows higher roles.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Admin can access analyst-minimum route
        """
        mock_get_role.return_value = 'admin'

        @require_minimum_role('analyst')
        def analyst_minimum_route():
            return {'message': 'analyst or higher'}

        result = analyst_minimum_route()

        assert result == {'message': 'analyst or higher'}

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_minimum_role_analyst_allows_analyst(self, mock_get_role):
        """Test minimum role allows exact match.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Analyst can access analyst-minimum route
        """
        mock_get_role.return_value = 'analyst'

        @require_minimum_role('analyst')
        def analyst_minimum_route():
            return {'message': 'analyst or higher'}

        result = analyst_minimum_route()

        assert result == {'message': 'analyst or higher'}

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_minimum_role_denies_lower_role(self, mock_get_role):
        """Test minimum role denies lower roles.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Viewer cannot access analyst-minimum route
        """
        mock_get_role.return_value = 'viewer'

        @require_minimum_role('analyst')
        def analyst_minimum_route():
            return {'message': 'analyst or higher'}

        with pytest.raises(InsufficientPermissionsError):
            analyst_minimum_route()

    def test_require_minimum_role_invalid_role_raises_error(self):
        """Test invalid minimum role raises ValueError.

        Assertions:
            - ValueError raised for unknown role
        """
        with pytest.raises(ValueError) as exc_info:
            @require_minimum_role('invalid_role')
            def test_route():
                pass

        assert 'invalid role' in str(exc_info.value).lower()

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_require_minimum_role_unauthenticated_raises_error(self, mock_get_role):
        """Test minimum role requires authentication.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - AuthorizationError raised when not authenticated
        """
        mock_get_role.return_value = None

        @require_minimum_role('viewer')
        def viewer_minimum_route():
            return {'message': 'authenticated users'}

        with pytest.raises(AuthorizationError):
            viewer_minimum_route()


class TestResourceOwnership:
    """Tests for resource ownership validation."""

    @patch('app.middleware.auth_middleware.get_current_user_id')
    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_check_resource_ownership_owner_grants_access(
        self,
        mock_get_role,
        mock_get_user_id
    ):
        """Test resource owner has access.

        Args:
            mock_get_role: Mocked get_current_user_role function
            mock_get_user_id: Mocked get_current_user_id function

        Assertions:
            - Owner can access their own resource
        """
        mock_get_user_id.return_value = 123
        mock_get_role.return_value = 'viewer'

        result = check_resource_ownership(resource_user_id=123)

        assert result is True

    @patch('app.middleware.auth_middleware.get_current_user_id')
    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_check_resource_ownership_admin_override(
        self,
        mock_get_role,
        mock_get_user_id
    ):
        """Test admin can access any resource with override enabled.

        Args:
            mock_get_role: Mocked get_current_user_role function
            mock_get_user_id: Mocked get_current_user_id function

        Assertions:
            - Admin can access others resources
        """
        mock_get_user_id.return_value = 123
        mock_get_role.return_value = 'admin'

        result = check_resource_ownership(resource_user_id=456, allow_admin_override=True)

        assert result is True

    @patch('app.middleware.auth_middleware.get_current_user_id')
    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_check_resource_ownership_admin_override_disabled(
        self,
        mock_get_role,
        mock_get_user_id
    ):
        """Test admin cannot access others resources when override disabled.

        Args:
            mock_get_role: Mocked get_current_user_role function
            mock_get_user_id: Mocked get_current_user_id function

        Assertions:
            - Admin denied when override is False
        """
        mock_get_user_id.return_value = 123
        mock_get_role.return_value = 'admin'

        result = check_resource_ownership(resource_user_id=456, allow_admin_override=False)

        assert result is False

    @patch('app.middleware.auth_middleware.get_current_user_id')
    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_check_resource_ownership_non_owner_denied(
        self,
        mock_get_role,
        mock_get_user_id
    ):
        """Test non-owner is denied access.

        Args:
            mock_get_role: Mocked get_current_user_role function
            mock_get_user_id: Mocked get_current_user_id function

        Assertions:
            - Non-owner viewer cannot access resource
        """
        mock_get_user_id.return_value = 123
        mock_get_role.return_value = 'viewer'

        result = check_resource_ownership(resource_user_id=456)

        assert result is False


class TestRequireResourceOwnershipDecorator:
    """Tests for require_resource_ownership decorator."""

    @patch('app.middleware.rbac_middleware.check_resource_ownership')
    def test_require_ownership_with_kwargs(self, mock_check_ownership):
        """Test ownership check with user_id in kwargs.

        Args:
            mock_check_ownership: Mocked check_resource_ownership function

        Assertions:
            - Function executes when ownership check passes
        """
        mock_check_ownership.return_value = True

        @require_resource_ownership()
        def update_profile(user_id):
            return {'user_id': user_id, 'updated': True}

        result = update_profile(user_id=123)

        assert result == {'user_id': 123, 'updated': True}
        mock_check_ownership.assert_called_once_with(123, True)

    @patch('app.middleware.rbac_middleware.check_resource_ownership')
    def test_require_ownership_with_args(self, mock_check_ownership):
        """Test ownership check with user_id in positional args.

        Args:
            mock_check_ownership: Mocked check_resource_ownership function

        Assertions:
            - Positional argument extracted correctly
        """
        mock_check_ownership.return_value = True

        @require_resource_ownership()
        def update_profile(user_id):
            return {'user_id': user_id, 'updated': True}

        result = update_profile(456)

        assert result == {'user_id': 456, 'updated': True}
        mock_check_ownership.assert_called_once_with(456, True)

    @patch('app.middleware.rbac_middleware.check_resource_ownership')
    def test_require_ownership_denied_raises_error(self, mock_check_ownership):
        """Test ownership check failure raises error.

        Args:
            mock_check_ownership: Mocked check_resource_ownership function

        Assertions:
            - AuthorizationError raised when ownership fails
        """
        mock_check_ownership.return_value = False

        @require_resource_ownership()
        def update_profile(user_id):
            return {'user_id': user_id, 'updated': True}

        with pytest.raises(AuthorizationError) as exc_info:
            update_profile(user_id=789)

        assert 'own resources' in str(exc_info.value).lower()

    def test_require_ownership_missing_user_id_raises_error(self):
        """Test missing user_id parameter raises ValueError.

        Assertions:
            - ValueError raised when user_id not provided
        """
        @require_resource_ownership()
        def update_profile():
            return {'updated': True}

        with pytest.raises(ValueError) as exc_info:
            update_profile()

        assert 'user_id parameter required' in str(exc_info.value).lower()

    @patch('app.middleware.rbac_middleware.check_resource_ownership')
    def test_require_ownership_admin_override_disabled(self, mock_check_ownership):
        """Test ownership decorator with admin override disabled.

        Args:
            mock_check_ownership: Mocked check_resource_ownership function

        Assertions:
            - allow_admin_override parameter passed correctly
        """
        mock_check_ownership.return_value = True

        @require_resource_ownership(allow_admin_override=False)
        def update_profile(user_id):
            return {'user_id': user_id}

        update_profile(user_id=123)

        mock_check_ownership.assert_called_once_with(123, False)


class TestUserPermissions:
    """Tests for permission system."""

    def test_get_user_permissions_admin(self):
        """Test admin permissions list.

        Assertions:
            - Admin has all permissions
            - Includes manage permissions
        """
        perms = get_user_permissions('admin')

        assert 'read:all' in perms
        assert 'write:all' in perms
        assert 'delete:all' in perms
        assert 'manage:users' in perms
        assert 'manage:settings' in perms
        assert 'view:analytics' in perms

    def test_get_user_permissions_analyst(self):
        """Test analyst permissions list.

        Assertions:
            - Analyst has read and analytics permissions
            - No write or delete permissions
        """
        perms = get_user_permissions('analyst')

        assert 'read:all' in perms
        assert 'view:analytics' in perms
        assert 'export:data' in perms
        assert 'write:all' not in perms
        assert 'delete:all' not in perms

    def test_get_user_permissions_viewer(self):
        """Test viewer permissions list.

        Assertions:
            - Viewer has minimal read-only permissions
        """
        perms = get_user_permissions('viewer')

        assert 'read:own' in perms
        assert 'view:dashboards' in perms
        assert 'read:all' not in perms
        assert 'manage:users' not in perms

    def test_get_user_permissions_invalid_role(self):
        """Test unknown role returns empty permissions.

        Assertions:
            - Empty list for invalid role
        """
        perms = get_user_permissions('invalid_role')

        assert perms == []


class TestHasPermission:
    """Tests for permission checking."""

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_has_permission_admin_has_all(self, mock_get_role):
        """Test admin has all permissions.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Admin has manage:users permission
        """
        mock_get_role.return_value = 'admin'

        result = has_permission('manage:users')

        assert result is True

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_has_permission_analyst_limited(self, mock_get_role):
        """Test analyst has limited permissions.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Analyst can view analytics
            - Analyst cannot manage users
        """
        mock_get_role.return_value = 'analyst'

        assert has_permission('view:analytics') is True
        assert has_permission('manage:users') is False

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_has_permission_viewer_minimal(self, mock_get_role):
        """Test viewer has minimal permissions.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Viewer can view dashboards
            - Viewer cannot read all data
        """
        mock_get_role.return_value = 'viewer'

        assert has_permission('view:dashboards') is True
        assert has_permission('read:all') is False

    def test_has_permission_with_explicit_role(self):
        """Test permission check with explicit role parameter.

        Assertions:
            - Explicit role used instead of current user
        """
        result = has_permission('manage:users', user_role='admin')

        assert result is True

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    def test_has_permission_no_role(self, mock_get_role):
        """Test permission check with no user role.

        Args:
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - Returns False when no role
        """
        mock_get_role.return_value = None

        result = has_permission('read:all')

        assert result is False


class TestRequirePermissionDecorator:
    """Tests for require_permission decorator."""

    @patch('app.middleware.rbac_middleware.has_permission')
    def test_require_permission_grants_access(self, mock_has_perm):
        """Test permission decorator grants access when permission exists.

        Args:
            mock_has_perm: Mocked has_permission function

        Assertions:
            - Function executes when permission check passes
        """
        mock_has_perm.return_value = True

        @require_permission('manage:users')
        def manage_users():
            return {'message': 'user management'}

        result = manage_users()

        assert result == {'message': 'user management'}
        mock_has_perm.assert_called_once_with('manage:users')

    @patch('app.middleware.rbac_middleware.get_current_user_role')
    @patch('app.middleware.rbac_middleware.has_permission')
    def test_require_permission_denies_access(self, mock_has_perm, mock_get_role):
        """Test permission decorator denies access when permission missing.

        Args:
            mock_has_perm: Mocked has_permission function
            mock_get_role: Mocked get_current_user_role function

        Assertions:
            - InsufficientPermissionsError raised
            - Error message mentions required permission
        """
        mock_has_perm.return_value = False
        mock_get_role.return_value = 'viewer'

        @require_permission('manage:users')
        def manage_users():
            return {'message': 'user management'}

        with pytest.raises(InsufficientPermissionsError) as exc_info:
            manage_users()

        assert 'manage:users' in str(exc_info.value)


class TestRoleHierarchyConstants:
    """Tests for role hierarchy constants."""

    def test_role_hierarchy_defined(self):
        """Test role hierarchy is properly defined.

        Assertions:
            - All expected roles present
            - Admin has highest level
            - Viewer has lowest level
        """
        assert 'admin' in ROLE_HIERARCHY
        assert 'analyst' in ROLE_HIERARCHY
        assert 'viewer' in ROLE_HIERARCHY

        assert ROLE_HIERARCHY['admin'] > ROLE_HIERARCHY['analyst']
        assert ROLE_HIERARCHY['analyst'] > ROLE_HIERARCHY['viewer']

    def test_role_hierarchy_numeric_values(self):
        """Test role hierarchy uses numeric levels.

        Assertions:
            - All values are integers
            - Values are positive
        """
        for role, level in ROLE_HIERARCHY.items():
            assert isinstance(level, int)
            assert level > 0

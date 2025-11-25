"""
Role-Based Access Control (RBAC) middleware.

This module provides decorators for role-based authorization:
- Require specific role(s)
- Require any of multiple roles
- Role hierarchy checking
"""

from functools import wraps
from typing import Callable, Any, List, Union
from flask import g, current_app
from app.exceptions.auth import InsufficientPermissionsError, AuthorizationError
from app.middleware.auth_middleware import get_current_user_role


# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    'admin': 3,
    'analyst': 2,
    'viewer': 1,
}


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to enforce role-based access control.

    User must have exactly one of the specified roles.
    Must be used with @jwt_required_custom decorator.

    Args:
        *allowed_roles: Variable number of allowed role names

    Returns:
        Decorator function

    Raises:
        InsufficientPermissionsError: If user role not in allowed_roles
        AuthorizationError: If user is not authenticated

    Example:
        >>> @jwt_required_custom()
        >>> @require_role("admin", "analyst")
        >>> def admin_only_route():
        >>>     return {"message": "Admin access granted"}
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current user role
            user_role = get_current_user_role()

            if not user_role:
                current_app.logger.warning("RBAC check failed: No user role found")
                raise AuthorizationError(
                    "Authentication required. Please provide a valid token."
                )

            # Check if user has required role
            if user_role not in allowed_roles:
                current_app.logger.warning(
                    f"RBAC check failed: User role '{user_role}' not in {allowed_roles}"
                )
                raise InsufficientPermissionsError(
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}"
                )

            current_app.logger.debug(f"RBAC check passed: User role '{user_role}'")
            return fn(*args, **kwargs)

        return wrapper
    return decorator


def require_any_role(*allowed_roles: str) -> Callable:
    """
    Alias for require_role for better code readability.

    Args:
        *allowed_roles: Variable number of allowed role names

    Returns:
        Decorator function

    Example:
        >>> @jwt_required_custom()
        >>> @require_any_role("admin", "analyst", "viewer")
        >>> def all_users_route():
        >>>     return {"message": "Accessible to all authenticated users"}
    """
    return require_role(*allowed_roles)


def require_admin() -> Callable:
    """
    Decorator to require admin role.

    Shorthand for @require_role("admin").

    Returns:
        Decorator function

    Example:
        >>> @jwt_required_custom()
        >>> @require_admin()
        >>> def admin_only():
        >>>     return {"message": "Admin only"}
    """
    return require_role("admin")


def require_analyst_or_admin() -> Callable:
    """
    Decorator to require analyst or admin role.

    Shorthand for @require_role("admin", "analyst").

    Returns:
        Decorator function

    Example:
        >>> @jwt_required_custom()
        >>> @require_analyst_or_admin()
        >>> def analytics_route():
        >>>     return {"data": "Analytics data"}
    """
    return require_role("admin", "analyst")


def require_minimum_role(minimum_role: str) -> Callable:
    """
    Decorator to require a minimum role level based on hierarchy.

    Allows users with the specified role or higher in the hierarchy.

    Args:
        minimum_role: Minimum required role

    Returns:
        Decorator function

    Raises:
        InsufficientPermissionsError: If user role is below minimum
        ValueError: If minimum_role is invalid

    Example:
        >>> @jwt_required_custom()
        >>> @require_minimum_role("analyst")
        >>> def analyst_and_above():
        >>>     # Accessible to analysts and admins
        >>>     return {"message": "Analyst or admin access"}
    """
    if minimum_role not in ROLE_HIERARCHY:
        raise ValueError(f"Invalid role: {minimum_role}")

    minimum_level = ROLE_HIERARCHY[minimum_role]

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user_role = get_current_user_role()

            if not user_role:
                raise AuthorizationError("Authentication required")

            user_level = ROLE_HIERARCHY.get(user_role, 0)

            if user_level < minimum_level:
                current_app.logger.warning(
                    f"RBAC check failed: User role '{user_role}' "
                    f"below minimum '{minimum_role}'"
                )
                raise InsufficientPermissionsError(
                    f"Access denied. Minimum required role: {minimum_role}"
                )

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def check_resource_ownership(
    resource_user_id: int,
    allow_admin_override: bool = True
) -> bool:
    """
    Check if current user owns a resource or is admin.

    Args:
        resource_user_id: User ID that owns the resource
        allow_admin_override: If True, admins can access any resource

    Returns:
        True if user has access, False otherwise

    Example:
        >>> @jwt_required_custom()
        >>> def get_user_profile(user_id: int):
        >>>     if not check_resource_ownership(user_id):
        >>>         raise AuthorizationError("Access denied")
        >>>     return get_profile(user_id)
    """
    from app.middleware.auth_middleware import get_current_user_id

    current_user_id = get_current_user_id()
    current_user_role = get_current_user_role()

    # User owns the resource
    if current_user_id == resource_user_id:
        return True

    # Admin override
    if allow_admin_override and current_user_role == 'admin':
        return True

    return False


def require_resource_ownership(allow_admin_override: bool = True) -> Callable:
    """
    Decorator to ensure user owns resource or is admin.

    Expects route parameter 'user_id' to check ownership.

    Args:
        allow_admin_override: If True, admins can access any resource

    Returns:
        Decorator function

    Raises:
        AuthorizationError: If user doesn't own resource and isn't admin

    Example:
        >>> @jwt_required_custom()
        >>> @require_resource_ownership()
        >>> def update_profile(user_id: int):
        >>>     # User can only update their own profile (or admin can update any)
        >>>     return update_user(user_id)
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get resource user_id from kwargs or args
            resource_user_id = kwargs.get('user_id')

            if resource_user_id is None:
                # Try to get from args (assuming first arg is user_id)
                if args:
                    resource_user_id = args[0]

            if resource_user_id is None:
                raise ValueError("user_id parameter required for ownership check")

            # Check ownership
            if not check_resource_ownership(resource_user_id, allow_admin_override):
                current_app.logger.warning(
                    f"Ownership check failed for resource user_id={resource_user_id}"
                )
                raise AuthorizationError(
                    "Access denied. You can only access your own resources."
                )

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def get_user_permissions(role: str) -> List[str]:
    """
    Get list of permissions for a role.

    This is a placeholder for future permission-based access control.
    Currently returns basic permissions based on role.

    Args:
        role: User role

    Returns:
        List of permission strings

    Example:
        >>> perms = get_user_permissions("admin")
        >>> print(perms)
        ['read:all', 'write:all', 'delete:all', 'manage:users']
    """
    role_permissions = {
        'admin': [
            'read:all',
            'write:all',
            'delete:all',
            'manage:users',
            'manage:settings',
            'view:analytics',
        ],
        'analyst': [
            'read:all',
            'view:analytics',
            'export:data',
        ],
        'viewer': [
            'read:own',
            'view:dashboards',
        ],
    }

    return role_permissions.get(role, [])


def has_permission(permission: str, user_role: Optional[str] = None) -> bool:
    """
    Check if user has specific permission.

    Args:
        permission: Permission string (e.g., 'read:all', 'manage:users')
        user_role: User role (optional, will use current user if None)

    Returns:
        True if user has permission, False otherwise

    Example:
        >>> if has_permission('manage:users'):
        >>>     # Allow user management operations
        >>>     pass
    """
    if user_role is None:
        user_role = get_current_user_role()

    if not user_role:
        return False

    user_permissions = get_user_permissions(user_role)
    return permission in user_permissions


def require_permission(permission: str) -> Callable:
    """
    Decorator to require specific permission.

    Args:
        permission: Required permission string

    Returns:
        Decorator function

    Raises:
        InsufficientPermissionsError: If user lacks permission

    Example:
        >>> @jwt_required_custom()
        >>> @require_permission('manage:users')
        >>> def manage_users():
        >>>     return {"message": "User management"}
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not has_permission(permission):
                user_role = get_current_user_role()
                current_app.logger.warning(
                    f"Permission check failed: User role '{user_role}' "
                    f"lacks permission '{permission}'"
                )
                raise InsufficientPermissionsError(
                    f"Access denied. Required permission: {permission}"
                )

            return fn(*args, **kwargs)

        return wrapper
    return decorator

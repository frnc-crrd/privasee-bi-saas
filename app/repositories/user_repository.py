"""User repository with user-specific database operations.

This module provides specialized repository for User model operations:
- User retrieval by email, username
- User search and filtering
- Role-based queries
- User statistics
- Authentication-related queries

Extends BaseRepository with user-specific business logic.

Usage:
    from app.repositories.user_repository import UserRepository

    repo = UserRepository()
    user = repo.get_by_email("john@example.com")
    active_admins = repo.get_by_role("admin", is_active=True)
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_, select

from app.exceptions import DatabaseException
from app.extensions import db
from app.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with specialized queries.

    Provides user-specific database operations beyond generic CRUD.
    All methods handle sessions and exceptions automatically.

    Example:
        >>> repo = UserRepository()
        >>> user = repo.get_by_email("john@example.com")
        >>> admins = repo.get_by_role("admin")
    """

    def __init__(self):
        """Initialize UserRepository with User model."""
        super().__init__(User)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.

        Args:
            email: User's email address (case-insensitive)

        Returns:
            User instance if found, None otherwise

        Example:
            >>> user = repo.get_by_email("john@example.com")
            >>> if user:
            ...     print(user.username)
        """
        return self.find_one_by(email=email.lower())

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: User's username (case-insensitive)

        Returns:
            User instance if found, None otherwise

        Example:
            >>> user = repo.get_by_username("john_doe")
            >>> if user:
            ...     print(user.email)
        """
        return self.find_one_by(username=username.lower())

    def get_by_email_or_username(self, identifier: str) -> Optional[User]:
        """Get user by email OR username.

        Useful for login where user can provide either identifier.

        Args:
            identifier: Email address or username

        Returns:
            User instance if found, None otherwise

        Example:
            >>> user = repo.get_by_email_or_username("john@example.com")
            >>> # Or
            >>> user = repo.get_by_email_or_username("john_doe")
        """
        try:
            query = select(User).where(
                or_(
                    func.lower(User.email) == identifier.lower(),
                    func.lower(User.username) == identifier.lower(),
                )
            )
            result = db.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseException(
                message="Failed to find user",
                details={"error": str(e), "identifier": identifier},
            ) from e

    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """Check if email already exists.

        Args:
            email: Email address to check
            exclude_id: Optional user ID to exclude from check (for updates)

        Returns:
            True if email exists, False otherwise

        Example:
            >>> if repo.email_exists("john@example.com"):
            ...     print("Email already taken")
            >>> # For updates, exclude current user
            >>> if repo.email_exists("new@example.com", exclude_id=123):
            ...     print("Email already taken by another user")
        """
        try:
            query = select(User).where(func.lower(User.email) == email.lower())
            if exclude_id:
                query = query.where(User.id != exclude_id)

            result = db.session.execute(query)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            raise DatabaseException(
                message="Failed to check email existence",
                details={"error": str(e), "email": email},
            ) from e

    def username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        """Check if username already exists.

        Args:
            username: Username to check
            exclude_id: Optional user ID to exclude from check (for updates)

        Returns:
            True if username exists, False otherwise

        Example:
            >>> if repo.username_exists("john_doe"):
            ...     print("Username already taken")
        """
        try:
            query = select(User).where(func.lower(User.username) == username.lower())
            if exclude_id:
                query = query.where(User.id != exclude_id)

            result = db.session.execute(query)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            raise DatabaseException(
                message="Failed to check username existence",
                details={"error": str(e), "username": username},
            ) from e

    def get_by_role(self, role: str, is_active: Optional[bool] = None) -> List[User]:
        """Get all users with specific role.

        Args:
            role: User role (admin, viewer, analyst)
            is_active: Optional filter by active status

        Returns:
            List of users with specified role

        Example:
            >>> admins = repo.get_by_role("admin")
            >>> active_analysts = repo.get_by_role("analyst", is_active=True)
        """
        filters = {"role": role.lower()}
        if is_active is not None:
            filters["is_active"] = is_active
        return self.filter_by(**filters)

    def get_active_users(self, limit: Optional[int] = None) -> List[User]:
        """Get all active users.

        Args:
            limit: Optional maximum number of users to return

        Returns:
            List of active users

        Example:
            >>> active_users = repo.get_active_users(limit=100)
        """
        return self.get_all(limit=limit) if limit else self.filter_by(is_active=True)

    def search_users(
        self,
        search_term: str,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
        limit: int = 50,
    ) -> List[User]:
        """Search users by username or email.

        Performs case-insensitive partial matching on username and email.

        Args:
            search_term: Term to search for in username/email
            is_active: Optional filter by active status
            role: Optional filter by role
            limit: Maximum number of results (default: 50)

        Returns:
            List of matching users

        Example:
            >>> users = repo.search_users("john")
            >>> active_admins = repo.search_users("admin", is_active=True, role="admin")
        """
        try:
            search_pattern = f"%{search_term.lower()}%"
            query = select(User).where(
                or_(
                    func.lower(User.username).like(search_pattern),
                    func.lower(User.email).like(search_pattern),
                )
            )

            if is_active is not None:
                query = query.where(User.is_active == is_active)

            if role:
                query = query.where(func.lower(User.role) == role.lower())

            query = query.limit(limit)

            result = db.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseException(
                message="Failed to search users",
                details={"error": str(e), "search_term": search_term},
            ) from e

    def get_users_created_after(self, date: datetime, limit: Optional[int] = None) -> List[User]:
        """Get users created after specific date.

        Args:
            date: Cutoff date
            limit: Optional maximum number of users

        Returns:
            List of users created after the date

        Example:
            >>> from datetime import datetime, timedelta
            >>> last_week = datetime.utcnow() - timedelta(days=7)
            >>> recent_users = repo.get_users_created_after(last_week)
        """
        try:
            query = select(User).where(User.created_at >= date).order_by(User.created_at.desc())

            if limit:
                query = query.limit(limit)

            result = db.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseException(
                message="Failed to fetch users by creation date",
                details={"error": str(e), "date": date.isoformat()},
            ) from e

    def get_users_by_date_range(self, start_date: datetime, end_date: datetime) -> List[User]:
        """Get users created within date range.

        Args:
            start_date: Range start date
            end_date: Range end date

        Returns:
            List of users created within range

        Example:
            >>> from datetime import datetime
            >>> start = datetime(2025, 1, 1)
            >>> end = datetime(2025, 1, 31)
            >>> january_users = repo.get_users_by_date_range(start, end)
        """
        try:
            query = select(User).where(
                and_(User.created_at >= start_date, User.created_at <= end_date)
            )

            result = db.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseException(
                message="Failed to fetch users by date range",
                details={
                    "error": str(e),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            ) from e

    def get_users_never_logged_in(self) -> List[User]:
        """Get users who have never logged in.

        Returns:
            List of users with null last_login

        Example:
            >>> never_logged_in = repo.get_users_never_logged_in()
        """
        try:
            query = select(User).where(User.last_login.is_(None))
            result = db.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseException(
                message="Failed to fetch users never logged in",
                details={"error": str(e)},
            ) from e

    def update_last_login(self, user_id: int, timestamp: Optional[datetime] = None) -> User:
        """Update user's last login timestamp.

        Args:
            user_id: User ID
            timestamp: Login timestamp (default: current UTC time)

        Returns:
            Updated user instance

        Example:
            >>> user = repo.update_last_login(123)
            >>> # Or with custom timestamp
            >>> user = repo.update_last_login(123, datetime.utcnow())
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return self.update(user_id, last_login=timestamp)

    def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            Updated user instance

        Example:
            >>> user = repo.deactivate_user(123)
            >>> assert not user.is_active
        """
        return self.update(user_id, is_active=False)

    def activate_user(self, user_id: int) -> User:
        """Activate a user account.

        Args:
            user_id: User ID

        Returns:
            Updated user instance

        Example:
            >>> user = repo.activate_user(123)
            >>> assert user.is_active
        """
        return self.update(user_id, is_active=True)

    def change_role(self, user_id: int, new_role: str) -> User:
        """Change user's role.

        Args:
            user_id: User ID
            new_role: New role (admin, viewer, analyst)

        Returns:
            Updated user instance

        Example:
            >>> user = repo.change_role(123, "admin")
            >>> assert user.role == "admin"
        """
        return self.update(user_id, role=new_role.lower())

    def get_user_stats(self) -> Dict[str, int]:
        """Get aggregate statistics about users.

        Returns:
            Dictionary with user statistics:
            - total_users: Total number of users
            - active_users: Number of active users
            - inactive_users: Number of inactive users
            - users_by_role: Dict of role:count
            - recent_registrations: Users registered in last 30 days

        Example:
            >>> stats = repo.get_user_stats()
            >>> print(f"Total users: {stats['total_users']}")
            >>> print(f"Admins: {stats['users_by_role']['admin']}")
        """
        try:
            # Total counts
            total_users = self.count()
            active_users = self.count(is_active=True)
            inactive_users = total_users - active_users

            # Count by role
            users_by_role: Dict[str, int] = {}
            for role in ["admin", "viewer", "analyst"]:
                users_by_role[role] = self.count(role=role)

            # Recent registrations (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_users = self.get_users_created_after(thirty_days_ago)
            recent_registrations = len(recent_users)

            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "users_by_role": users_by_role,
                "recent_registrations": recent_registrations,
            }
        except Exception as e:
            raise DatabaseException(
                message="Failed to get user statistics",
                details={"error": str(e)},
            ) from e

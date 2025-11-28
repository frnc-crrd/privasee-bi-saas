"""
Unit tests for user repository module.

This module contains comprehensive tests for user-specific database
operations and queries.

Test Coverage:
    - User retrieval by email, username, or either
    - Email and username existence checks
    - Role-based queries
    - User search functionality
    - Date-based filtering
    - User statistics
    - User status management (activate, deactivate)
    - Last login tracking

Business Value:
    - Ensures user authentication queries work correctly
    - Validates user management operations
    - Confirms data integrity for user operations
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.user_repository import UserRepository
from app.models import User
from app.exceptions.base import DatabaseException


@pytest.fixture
def user_repo(db):
    """Create user repository for testing."""
    return UserRepository()


@pytest.fixture
def sample_users(db):
    """Create sample users for testing."""
    users = []

    # Admin user
    admin = User(username='admin_user', email='admin@example.com', role='admin', is_active=True)
    admin.set_password('Password123!')
    db.session.add(admin)
    users.append(admin)

    # Analyst user
    analyst = User(username='analyst_user', email='analyst@example.com', role='analyst', is_active=True)
    analyst.set_password('Password123!')
    analyst.last_login = datetime.now(timezone.utc)
    db.session.add(analyst)
    users.append(analyst)

    # Viewer user (inactive)
    viewer = User(username='viewer_user', email='viewer@example.com', role='viewer', is_active=False)
    viewer.set_password('Password123!')
    db.session.add(viewer)
    users.append(viewer)

    # User who never logged in
    new_user = User(username='new_user', email='new@example.com', role='viewer', is_active=True)
    new_user.set_password('Password123!')
    db.session.add(new_user)
    users.append(new_user)

    db.session.commit()
    return users


class TestUserRetrieval:
    """Tests for user retrieval methods."""

    def test_get_by_email_exists(self, user_repo, sample_users, db):
        """Test retrieving user by email."""
        user = user_repo.get_by_email('admin@example.com')

        assert user is not None
        assert user.username == 'admin_user'

    def test_get_by_email_case_insensitive(self, user_repo, sample_users, db):
        """Test email lookup is case-insensitive."""
        user = user_repo.get_by_email('ADMIN@EXAMPLE.COM')

        assert user is not None
        assert user.email == 'admin@example.com'

    def test_get_by_email_not_found(self, user_repo, db):
        """Test get_by_email returns None when not found."""
        user = user_repo.get_by_email('nonexistent@example.com')

        assert user is None

    def test_get_by_username_exists(self, user_repo, sample_users, db):
        """Test retrieving user by username."""
        user = user_repo.get_by_username('analyst_user')

        assert user is not None
        assert user.role == 'analyst'

    def test_get_by_username_case_insensitive(self, user_repo, sample_users, db):
        """Test username lookup is case-insensitive."""
        user = user_repo.get_by_username('ANALYST_USER')

        assert user is not None

    def test_get_by_email_or_username_with_email(self, user_repo, sample_users, db):
        """Test retrieving user by email using email_or_username."""
        user = user_repo.get_by_email_or_username('admin@example.com')

        assert user is not None
        assert user.username == 'admin_user'

    def test_get_by_email_or_username_with_username(self, user_repo, sample_users, db):
        """Test retrieving user by username using email_or_username."""
        user = user_repo.get_by_email_or_username('analyst_user')

        assert user is not None
        assert user.email == 'analyst@example.com'

    def test_get_by_email_or_username_not_found(self, user_repo, db):
        """Test email_or_username returns None when not found."""
        user = user_repo.get_by_email_or_username('nonexistent')

        assert user is None


class TestExistenceChecks:
    """Tests for email and username existence checks."""

    def test_email_exists_returns_true(self, user_repo, sample_users, db):
        """Test email_exists returns True for existing email."""
        exists = user_repo.email_exists('admin@example.com')

        assert exists is True

    def test_email_exists_returns_false(self, user_repo, db):
        """Test email_exists returns False for non-existent email."""
        exists = user_repo.email_exists('notfound@example.com')

        assert exists is False

    def test_email_exists_with_exclude_id(self, user_repo, sample_users, db):
        """Test email_exists excludes specific user ID."""
        admin = sample_users[0]

        # Same email but exclude the admin user
        exists = user_repo.email_exists('admin@example.com', exclude_id=admin.id)

        assert exists is False

    def test_username_exists_returns_true(self, user_repo, sample_users, db):
        """Test username_exists returns True for existing username."""
        exists = user_repo.username_exists('admin_user')

        assert exists is True

    def test_username_exists_returns_false(self, user_repo, db):
        """Test username_exists returns False for non-existent username."""
        exists = user_repo.username_exists('nonexistent')

        assert exists is False

    def test_username_exists_with_exclude_id(self, user_repo, sample_users, db):
        """Test username_exists excludes specific user ID."""
        admin = sample_users[0]

        exists = user_repo.username_exists('admin_user', exclude_id=admin.id)

        assert exists is False


class TestRoleBasedQueries:
    """Tests for role-based user queries."""

    def test_get_by_role_returns_matching_users(self, user_repo, sample_users, db):
        """Test get_by_role returns users with specified role."""
        admins = user_repo.get_by_role('admin')

        assert len(admins) >= 1
        assert all(u.role == 'admin' for u in admins)

    def test_get_by_role_with_is_active_filter(self, user_repo, sample_users, db):
        """Test get_by_role with is_active filter."""
        active_viewers = user_repo.get_by_role('viewer', is_active=True)

        assert all(u.role == 'viewer' and u.is_active for u in active_viewers)

    def test_get_active_users(self, user_repo, sample_users, db):
        """Test get_active_users returns only active users."""
        active_users = user_repo.get_active_users()

        assert len(active_users) >= 2
        assert all(u.is_active for u in active_users)

    def test_get_active_users_with_limit(self, user_repo, sample_users, db):
        """Test get_active_users respects limit parameter."""
        active_users = user_repo.get_active_users(limit=1)

        assert len(active_users) == 1


class TestUserSearch:
    """Tests for user search functionality."""

    def test_search_users_by_username(self, user_repo, sample_users, db):
        """Test searching users by username pattern."""
        users = user_repo.search_users('admin')

        assert len(users) >= 1
        assert any('admin' in u.username.lower() for u in users)

    def test_search_users_by_email(self, user_repo, sample_users, db):
        """Test searching users by email pattern."""
        users = user_repo.search_users('analyst@')

        assert len(users) >= 1
        assert any('analyst@' in u.email.lower() for u in users)

    def test_search_users_with_role_filter(self, user_repo, sample_users, db):
        """Test search with role filter."""
        users = user_repo.search_users('user', role='admin')

        assert all(u.role == 'admin' for u in users)

    def test_search_users_with_is_active_filter(self, user_repo, sample_users, db):
        """Test search with is_active filter."""
        users = user_repo.search_users('user', is_active=True)

        assert all(u.is_active for u in users)

    def test_search_users_respects_limit(self, user_repo, sample_users, db):
        """Test search respects limit parameter."""
        users = user_repo.search_users('user', limit=2)

        assert len(users) <= 2


class TestDateBasedQueries:
    """Tests for date-based filtering."""

    def test_get_users_created_after(self, user_repo, sample_users, db):
        """Test retrieving users created after specific date."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        users = user_repo.get_users_created_after(yesterday)

        assert len(users) >= 1
        # created_at is timezone-naive in DB, so we need to make yesterday naive
        yesterday_naive = yesterday.replace(tzinfo=None)
        assert all(u.created_at >= yesterday_naive for u in users)

    def test_get_users_created_after_with_limit(self, user_repo, sample_users, db):
        """Test get_users_created_after respects limit."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        users = user_repo.get_users_created_after(yesterday, limit=2)

        assert len(users) <= 2

    def test_get_users_by_date_range(self, user_repo, sample_users, db):
        """Test retrieving users within date range."""
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc) + timedelta(days=1)

        users = user_repo.get_users_by_date_range(start, end)

        assert len(users) >= 1
        # Convert to naive for comparison
        start_naive = start.replace(tzinfo=None)
        end_naive = end.replace(tzinfo=None)
        assert all(start_naive <= u.created_at <= end_naive for u in users)

    def test_get_users_never_logged_in(self, user_repo, sample_users, db):
        """Test retrieving users who never logged in."""
        users = user_repo.get_users_never_logged_in()

        assert len(users) >= 1
        assert all(u.last_login is None for u in users)


class TestUserStatusManagement:
    """Tests for user activation and deactivation."""

    def test_deactivate_user(self, user_repo, sample_users, db):
        """Test deactivating user account."""
        admin = sample_users[0]

        updated = user_repo.deactivate_user(admin.id)

        assert updated.is_active is False

    def test_activate_user(self, user_repo, sample_users, db):
        """Test activating user account."""
        viewer = sample_users[2]  # Inactive viewer

        updated = user_repo.activate_user(viewer.id)

        assert updated.is_active is True

    def test_change_role(self, user_repo, sample_users, db):
        """Test changing user role."""
        viewer = sample_users[2]

        updated = user_repo.change_role(viewer.id, 'analyst')

        assert updated.role == 'analyst'

    def test_update_last_login_with_default_timestamp(self, user_repo, sample_users, db):
        """Test updating last login with default timestamp."""
        user = sample_users[3]  # User who never logged in

        updated = user_repo.update_last_login(user.id)

        assert updated.last_login is not None

    def test_update_last_login_with_custom_timestamp(self, user_repo, sample_users, db):
        """Test updating last login with custom timestamp."""
        user = sample_users[3]
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = user_repo.update_last_login(user.id, custom_time)

        # DB stores timezone-naive datetime
        expected_time = custom_time.replace(tzinfo=None)
        assert updated.last_login == expected_time


class TestUserStatistics:
    """Tests for user statistics aggregation."""

    def test_get_user_stats_returns_all_metrics(self, user_repo, sample_users, db):
        """Test get_user_stats returns complete statistics."""
        stats = user_repo.get_user_stats()

        assert 'total_users' in stats
        assert 'active_users' in stats
        assert 'inactive_users' in stats
        assert 'users_by_role' in stats
        assert 'recent_registrations' in stats

    def test_get_user_stats_calculates_totals_correctly(self, user_repo, sample_users, db):
        """Test user statistics calculations."""
        stats = user_repo.get_user_stats()

        assert stats['total_users'] >= 4
        assert stats['active_users'] >= 2
        assert stats['inactive_users'] >= 1

    def test_get_user_stats_counts_by_role(self, user_repo, sample_users, db):
        """Test user statistics by role."""
        stats = user_repo.get_user_stats()

        assert 'admin' in stats['users_by_role']
        assert 'analyst' in stats['users_by_role']
        assert 'viewer' in stats['users_by_role']


class TestErrorHandling:
    """Tests for error handling in repository methods."""

    def test_get_by_email_or_username_database_error(self, user_repo, db):
        """Test database error handling in get_by_email_or_username."""
        with patch('app.repositories.user_repository.db.session.execute') as mock_execute:
            mock_execute.side_effect = SQLAlchemyError("Database error")

            with pytest.raises(DatabaseException):
                user_repo.get_by_email_or_username('test@example.com')

    def test_email_exists_database_error(self, user_repo, db):
        """Test database error handling in email_exists."""
        with patch('app.repositories.user_repository.db.session.execute') as mock_execute:
            mock_execute.side_effect = Exception("Database error")

            with pytest.raises(DatabaseException):
                user_repo.email_exists('test@example.com')

    def test_search_users_database_error(self, user_repo, db):
        """Test database error handling in search_users."""
        with patch('app.repositories.user_repository.db.session.execute') as mock_execute:
            mock_execute.side_effect = Exception("Database error")

            with pytest.raises(DatabaseException):
                user_repo.search_users('test')

    def test_get_user_stats_database_error(self, user_repo, db):
        """Test database error handling in get_user_stats."""
        with patch.object(user_repo, 'count') as mock_count:
            mock_count.side_effect = Exception("Database error")

            with pytest.raises(DatabaseException):
                user_repo.get_user_stats()

"""
Integration tests for user management routes.

Tests cover:
- List users (with pagination and filtering)
- Get user by ID
- Update user
- Deactivate user
- Activate user
- Get user statistics
- RBAC authorization checks
"""

import pytest
from flask import json


class TestListUsers:
    """Tests for GET /api/v1/users endpoint."""

    def test_list_users_as_admin(self, client, db, admin_user, viewer_user, auth_headers):
        """Test admin can list all users."""
        response = client.get(
            "/api/v1/users",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "users" in data["data"]
        assert "pagination" in data["meta"]
        assert len(data["data"]["users"]) >= 2  # At least admin and viewer

    def test_list_users_as_analyst(self, client, db, analyst_user, analyst_headers):
        """Test analyst can list users."""
        response = client.get(
            "/api/v1/users",
            headers=analyst_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    def test_list_users_as_viewer(self, client, db, viewer_user, viewer_headers):
        """Test viewer cannot list users."""
        response = client.get(
            "/api/v1/users",
            headers=viewer_headers
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False
        assert "permission" in data["error"]["message"].lower()

    def test_list_users_with_pagination(self, client, db, auth_headers):
        """Test user list pagination."""
        response = client.get(
            "/api/v1/users?page=1&per_page=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["meta"]["pagination"]["page"] == 1
        assert data["meta"]["pagination"]["per_page"] == 10

    def test_list_users_with_role_filter(self, client, db, admin_user, viewer_user, auth_headers):
        """Test filtering users by role."""
        response = client.get(
            "/api/v1/users?role=admin",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        # All returned users should be admins
        for user in data["data"]["users"]:
            assert user["role"] == "admin"

    def test_list_users_without_auth(self, client, db):
        """Test listing users without authentication."""
        response = client.get("/api/v1/users")

        assert response.status_code == 401


class TestGetUser:
    """Tests for GET /api/v1/users/{id} endpoint."""

    def test_get_own_profile(self, client, db, admin_user, auth_headers):
        """Test user can get their own profile."""
        response = client.get(
            f"/api/v1/users/{admin_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["user"]["id"] == admin_user.id
        assert data["data"]["user"]["email"] == admin_user.email

    def test_get_other_user_as_admin(self, client, db, admin_user, viewer_user, auth_headers):
        """Test admin can get other user's profile."""
        response = client.get(
            f"/api/v1/users/{viewer_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["data"]["user"]["id"] == viewer_user.id

    def test_get_other_user_as_viewer(self, client, db, admin_user, viewer_user, viewer_headers):
        """Test viewer cannot get other user's profile."""
        response = client.get(
            f"/api/v1/users/{admin_user.id}",
            headers=viewer_headers
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False

    def test_get_nonexistent_user(self, client, db, auth_headers):
        """Test getting nonexistent user."""
        response = client.get(
            "/api/v1/users/99999",
            headers=auth_headers
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False

    def test_get_user_without_auth(self, client, db, admin_user):
        """Test getting user without authentication."""
        response = client.get(f"/api/v1/users/{admin_user.id}")

        assert response.status_code == 401


class TestUpdateUser:
    """Tests for PUT /api/v1/users/{id} endpoint."""

    def test_update_own_username(self, client, db, admin_user, auth_headers):
        """Test user can update their own username."""
        payload = {"username": "new_admin_username"}

        response = client.put(
            f"/api/v1/users/{admin_user.id}",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["user"]["username"] == "new_admin_username"

    def test_update_own_email(self, client, db, admin_user, auth_headers):
        """Test user can update their own email."""
        payload = {"email": "newemail@test.com"}

        response = client.put(
            f"/api/v1/users/{admin_user.id}",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["data"]["user"]["email"] == "newemail@test.com"

    def test_viewer_cannot_update_role(self, client, db, viewer_user, viewer_headers):
        """Test viewer cannot update their own role."""
        payload = {"role": "admin"}

        response = client.put(
            f"/api/v1/users/{viewer_user.id}",
            data=json.dumps(payload),
            content_type="application/json",
            headers=viewer_headers
        )

        # Should either be forbidden or role should not change
        assert response.status_code in [200, 400, 403]
        if response.status_code == 200:
            data = json.loads(response.data)
            # Role should not have changed
            assert data["data"]["user"]["role"] != "admin"

    def test_admin_can_update_user_role(self, client, db, viewer_user, auth_headers):
        """Test admin can update other user's role."""
        payload = {"role": "analyst"}

        response = client.put(
            f"/api/v1/users/{viewer_user.id}",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["data"]["user"]["role"] == "analyst"

    def test_update_with_duplicate_email(self, client, db, admin_user, viewer_user, auth_headers):
        """Test updating to duplicate email fails."""
        payload = {"email": viewer_user.email}

        response = client.put(
            f"/api/v1/users/{admin_user.id}",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "already registered" in data["error"]["message"].lower()

    def test_viewer_cannot_update_other_user(self, client, db, admin_user, viewer_headers):
        """Test viewer cannot update other user."""
        payload = {"username": "hacked_username"}

        response = client.put(
            f"/api/v1/users/{admin_user.id}",
            data=json.dumps(payload),
            content_type="application/json",
            headers=viewer_headers
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False


class TestDeactivateUser:
    """Tests for DELETE /api/v1/users/{id} endpoint."""

    def test_admin_can_deactivate_user(self, client, db, viewer_user, auth_headers):
        """Test admin can deactivate user."""
        response = client.delete(
            f"/api/v1/users/{viewer_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["is_active"] is False

    def test_admin_cannot_deactivate_self(self, client, db, admin_user, auth_headers):
        """Test admin cannot deactivate their own account."""
        response = client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "cannot deactivate" in data["error"]["message"].lower()

    def test_viewer_cannot_deactivate_user(self, client, db, admin_user, viewer_headers):
        """Test viewer cannot deactivate users."""
        response = client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers=viewer_headers
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False

    def test_deactivate_without_auth(self, client, db, viewer_user):
        """Test deactivating user without authentication."""
        response = client.delete(f"/api/v1/users/{viewer_user.id}")

        assert response.status_code == 401


class TestActivateUser:
    """Tests for POST /api/v1/users/{id}/activate endpoint."""

    def test_admin_can_activate_user(self, client, db, inactive_user, auth_headers):
        """Test admin can activate inactive user."""
        response = client.post(
            f"/api/v1/users/{inactive_user.id}/activate",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["is_active"] is True

    def test_viewer_cannot_activate_user(self, client, db, inactive_user, viewer_headers):
        """Test viewer cannot activate users."""
        response = client.post(
            f"/api/v1/users/{inactive_user.id}/activate",
            headers=viewer_headers
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False

    def test_activate_without_auth(self, client, db, inactive_user):
        """Test activating user without authentication."""
        response = client.post(f"/api/v1/users/{inactive_user.id}/activate")

        assert response.status_code == 401


class TestUserStatistics:
    """Tests for GET /api/v1/users/stats endpoint."""

    def test_admin_can_get_stats(self, client, db, admin_user, viewer_user, auth_headers):
        """Test admin can get user statistics."""
        response = client.get(
            "/api/v1/users/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        # Statistics should contain total counts and breakdowns
        assert "total_users" in data["data"] or "users" in str(data["data"])

    def test_analyst_can_get_stats(self, client, db, analyst_headers):
        """Test analyst can get user statistics."""
        response = client.get(
            "/api/v1/users/stats",
            headers=analyst_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    def test_viewer_cannot_get_stats(self, client, db, viewer_headers):
        """Test viewer cannot get user statistics."""
        response = client.get(
            "/api/v1/users/stats",
            headers=viewer_headers
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False

    def test_get_stats_without_auth(self, client, db):
        """Test getting statistics without authentication."""
        response = client.get("/api/v1/users/stats")

        assert response.status_code == 401

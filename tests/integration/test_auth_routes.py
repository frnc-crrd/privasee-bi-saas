"""
Integration tests for authentication routes.

Tests cover:
- User registration (success and failure cases)
- User login (success and failure cases)
- Token refresh
- User logout
- Password change
- Get current user info
"""

import pytest
from flask import json


class TestAuthRegister:
    """Tests for POST /api/v1/auth/register endpoint."""

    def test_register_success(self, client, db):
        """Test successful user registration."""
        payload = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "SecurePass123!",
            "role": "viewer"
        }

        response = client.post(
            "/api/v1/auth/register",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert "user" in data["data"]
        assert "tokens" in data["data"]
        assert data["data"]["user"]["username"] == "newuser"
        assert data["data"]["user"]["email"] == "newuser@test.com"
        assert data["data"]["user"]["role"] == "viewer"
        assert "access_token" in data["data"]["tokens"]
        assert "refresh_token" in data["data"]["tokens"]

    def test_register_duplicate_email(self, client, db, admin_user):
        """Test registration with duplicate email."""
        payload = {
            "username": "different_username",
            "email": admin_user.email,  # Duplicate email
            "password": "SecurePass123!",
            "role": "viewer"
        }

        response = client.post(
            "/api/v1/auth/register",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data["success"] is False
        assert "already exists" in data["error"]["message"].lower()

    def test_register_duplicate_username(self, client, db, admin_user):
        """Test registration with duplicate username."""
        payload = {
            "username": admin_user.username,  # Duplicate username
            "email": "unique@test.com",
            "password": "SecurePass123!",
            "role": "viewer"
        }

        response = client.post(
            "/api/v1/auth/register",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data["success"] is False
        assert "already taken" in data["error"]["message"].lower()

    def test_register_weak_password(self, client, db):
        """Test registration with weak password."""
        payload = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "weak",  # Too short, no uppercase, no digit, no special char
            "role": "viewer"
        }

        response = client.post(
            "/api/v1/auth/register",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    def test_register_invalid_email(self, client, db):
        """Test registration with invalid email."""
        payload = {
            "username": "newuser",
            "email": "invalid-email",  # No @ sign
            "password": "SecurePass123!",
            "role": "viewer"
        }

        response = client.post(
            "/api/v1/auth/register",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    def test_register_invalid_role(self, client, db):
        """Test registration with invalid role."""
        payload = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "SecurePass123!",
            "role": "superadmin"  # Invalid role
        }

        response = client.post(
            "/api/v1/auth/register",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False


class TestAuthLogin:
    """Tests for POST /api/v1/auth/login endpoint."""

    def test_login_success(self, client, db, admin_user):
        """Test successful login."""
        payload = {
            "email": admin_user.email,
            "password": "AdminPass123!"
        }

        response = client.post(
            "/api/v1/auth/login",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "user" in data["data"]
        assert "tokens" in data["data"]
        assert data["data"]["user"]["email"] == admin_user.email
        assert "access_token" in data["data"]["tokens"]
        assert "refresh_token" in data["data"]["tokens"]

    def test_login_invalid_credentials(self, client, db, admin_user):
        """Test login with wrong password."""
        payload = {
            "email": admin_user.email,
            "password": "WrongPassword123!"
        }

        response = client.post(
            "/api/v1/auth/login",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "invalid" in data["error"]["message"].lower()

    def test_login_nonexistent_user(self, client, db):
        """Test login with nonexistent email."""
        payload = {
            "email": "nonexistent@test.com",
            "password": "SomePassword123!"
        }

        response = client.post(
            "/api/v1/auth/login",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False

    def test_login_inactive_user(self, client, db, inactive_user):
        """Test login with inactive account."""
        payload = {
            "email": inactive_user.email,
            "password": "InactivePass123!"
        }

        response = client.post(
            "/api/v1/auth/login",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "disabled" in data["error"]["message"].lower()


class TestAuthRefresh:
    """Tests for POST /api/v1/auth/refresh endpoint."""

    def test_refresh_token_success(self, client, db, admin_refresh_token):
        """Test successful token refresh."""
        headers = {"Authorization": f"Bearer {admin_refresh_token}"}

        response = client.post(
            "/api/v1/auth/refresh",
            headers=headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "token_type" in data["data"]
        assert data["data"]["token_type"] == "Bearer"

    def test_refresh_token_missing(self, client, db):
        """Test refresh without token."""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401

    def test_refresh_with_access_token(self, client, db, admin_token):
        """Test refresh with access token instead of refresh token."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/auth/refresh",
            headers=headers
        )

        # Should fail because access token is not a refresh token
        assert response.status_code in [401, 422]


class TestAuthLogout:
    """Tests for POST /api/v1/auth/logout endpoint."""

    def test_logout_success(self, client, db, auth_headers):
        """Test successful logout."""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "logout" in data["error"]["message"].lower()

    def test_logout_without_token(self, client, db):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestAuthPasswordChange:
    """Tests for POST /api/v1/auth/password/change endpoint."""

    def test_change_password_success(self, client, db, admin_user, auth_headers):
        """Test successful password change."""
        payload = {
            "old_password": "AdminPass123!",
            "new_password": "NewAdminPass456!"
        }

        response = client.post(
            "/api/v1/auth/password/change",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "changed" in data["error"]["message"].lower()

        # Verify new password works
        login_payload = {
            "email": admin_user.email,
            "password": "NewAdminPass456!"
        }
        login_response = client.post(
            "/api/v1/auth/login",
            data=json.dumps(login_payload),
            content_type="application/json"
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_old_password(self, client, db, auth_headers):
        """Test password change with wrong old password."""
        payload = {
            "old_password": "WrongOldPassword123!",
            "new_password": "NewAdminPass456!"
        }

        response = client.post(
            "/api/v1/auth/password/change",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "incorrect" in data["error"]["message"].lower()

    def test_change_password_weak_new_password(self, client, db, auth_headers):
        """Test password change with weak new password."""
        payload = {
            "old_password": "AdminPass123!",
            "new_password": "weak"
        }

        response = client.post(
            "/api/v1/auth/password/change",
            data=json.dumps(payload),
            content_type="application/json",
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    def test_change_password_without_token(self, client, db):
        """Test password change without authentication."""
        payload = {
            "old_password": "AdminPass123!",
            "new_password": "NewAdminPass456!"
        }

        response = client.post(
            "/api/v1/auth/password/change",
            data=json.dumps(payload),
            content_type="application/json"
        )

        assert response.status_code == 401


class TestAuthGetCurrentUser:
    """Tests for GET /api/v1/auth/me endpoint."""

    def test_get_current_user_success(self, client, db, admin_user, auth_headers):
        """Test getting current user info."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "user" in data["data"]
        assert data["data"]["user"]["id"] == admin_user.id
        assert data["data"]["user"]["username"] == admin_user.username
        assert data["data"]["user"]["email"] == admin_user.email
        assert data["data"]["user"]["role"] == admin_user.role

    def test_get_current_user_without_token(self, client, db):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

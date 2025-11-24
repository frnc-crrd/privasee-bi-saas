"""Unit tests for app.schemas.auth_schemas module.

Tests all authentication and authorization schemas.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth_schemas import (
    AuthStatusResponse,
    ChangePasswordRequest,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)


class TestLoginRequest:
    """Test LoginRequest schema."""

    def test_login_with_email(self):
        """Test login with email."""
        data = {
            "email": "user@example.com",
            "password": "password123",
        }
        login = LoginRequest(**data)
        assert login.email == "user@example.com"
        assert login.password == "password123"
        assert login.remember_me is False

    def test_login_with_username(self):
        """Test login with username."""
        data = {
            "username": "john_doe",
            "password": "password123",
        }
        login = LoginRequest(**data)
        assert login.username == "john_doe"
        assert login.password == "password123"

    def test_login_with_remember_me(self):
        """Test login with remember_me flag."""
        data = {
            "email": "user@example.com",
            "password": "password123",
            "remember_me": True,
        }
        login = LoginRequest(**data)
        assert login.remember_me is True

    def test_login_missing_password(self):
        """Test that login without password fails."""
        data = {"email": "user@example.com"}
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(**data)
        assert "password" in str(exc_info.value)

    def test_login_invalid_email(self):
        """Test that login with invalid email fails."""
        data = {
            "email": "invalid-email",
            "password": "password123",
        }
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(**data)
        assert "email" in str(exc_info.value).lower()


class TestRegisterRequest:
    """Test RegisterRequest schema."""

    def test_valid_registration(self):
        """Test valid registration request."""
        data = {
            "email": "newuser@example.com",
            "username": "new_user",
            "password": "StrongP@ss123",
            "password_confirm": "StrongP@ss123",
        }
        register = RegisterRequest(**data)
        assert register.email == "newuser@example.com"
        assert register.username == "new_user"
        assert register.password == "StrongP@ss123"

    def test_registration_passwords_dont_match(self):
        """Test that mismatched passwords fail."""
        data = {
            "email": "newuser@example.com",
            "username": "new_user",
            "password": "StrongP@ss123",
            "password_confirm": "DifferentP@ss123",
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(**data)
        assert "do not match" in str(exc_info.value).lower()

    def test_registration_weak_password(self):
        """Test that weak passwords fail."""
        data = {
            "email": "newuser@example.com",
            "username": "new_user",
            "password": "weak",
            "password_confirm": "weak",
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(**data)
        assert "password" in str(exc_info.value).lower()

    def test_registration_invalid_username(self):
        """Test that invalid usernames fail."""
        data = {
            "email": "newuser@example.com",
            "username": "ab",  # Too short
            "password": "StrongP@ss123",
            "password_confirm": "StrongP@ss123",
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(**data)
        assert "username" in str(exc_info.value).lower()

    def test_registration_reserved_username(self):
        """Test that reserved usernames fail."""
        data = {
            "email": "newuser@example.com",
            "username": "admin",
            "password": "StrongP@ss123",
            "password_confirm": "StrongP@ss123",
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(**data)
        assert "reserved" in str(exc_info.value).lower()

    def test_registration_disposable_email(self):
        """Test that disposable emails fail."""
        data = {
            "email": "user@tempmail.com",
            "username": "new_user",
            "password": "StrongP@ss123",
            "password_confirm": "StrongP@ss123",
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(**data)
        assert "disposable" in str(exc_info.value).lower()


class TestTokenResponse:
    """Test TokenResponse schema."""

    def test_valid_token_response(self):
        """Test valid token response."""
        data = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJh...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJh...",
            "expires_in": 3600,
            "user_id": 123,
            "username": "john_doe",
            "role": "admin",
        }
        token = TokenResponse(**data)
        assert token.access_token == "eyJ0eXAiOiJKV1QiLCJh..."
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.user_id == 123

    def test_token_response_missing_access_token(self):
        """Test that token response without access_token fails."""
        data = {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJh...",
            "expires_in": 3600,
            "user_id": 123,
            "username": "john_doe",
            "role": "admin",
        }
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse(**data)
        assert "access_token" in str(exc_info.value)


class TestRefreshTokenRequest:
    """Test RefreshTokenRequest schema."""

    def test_valid_refresh_token_request(self):
        """Test valid refresh token request."""
        data = {"refresh_token": "eyJ0eXAiOiJKV1QiLCJh..."}
        refresh = RefreshTokenRequest(**data)
        assert refresh.refresh_token == "eyJ0eXAiOiJKV1QiLCJh..."

    def test_refresh_token_missing(self):
        """Test that request without refresh_token fails."""
        with pytest.raises(ValidationError) as exc_info:
            RefreshTokenRequest(**{})
        assert "refresh_token" in str(exc_info.value)


class TestPasswordResetRequest:
    """Test PasswordResetRequest schema."""

    def test_valid_password_reset_request(self):
        """Test valid password reset request."""
        data = {"email": "user@example.com"}
        reset = PasswordResetRequest(**data)
        assert reset.email == "user@example.com"

    def test_password_reset_invalid_email(self):
        """Test that invalid email fails."""
        data = {"email": "invalid-email"}
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetRequest(**data)
        assert "email" in str(exc_info.value).lower()

    def test_password_reset_disposable_email(self):
        """Test that disposable email fails."""
        data = {"email": "user@tempmail.com"}
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetRequest(**data)
        assert "disposable" in str(exc_info.value).lower()


class TestPasswordResetConfirmRequest:
    """Test PasswordResetConfirmRequest schema."""

    def test_valid_password_reset_confirm(self):
        """Test valid password reset confirmation."""
        data = {
            "token": "abc123def456",
            "password": "NewP@ssw0rd",
            "password_confirm": "NewP@ssw0rd",
        }
        confirm = PasswordResetConfirmRequest(**data)
        assert confirm.token == "abc123def456"
        assert confirm.password == "NewP@ssw0rd"

    def test_password_reset_confirm_passwords_dont_match(self):
        """Test that mismatched passwords fail."""
        data = {
            "token": "abc123def456",
            "password": "NewP@ssw0rd",
            "password_confirm": "DifferentP@ssw0rd",
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(**data)
        assert "do not match" in str(exc_info.value).lower()

    def test_password_reset_confirm_weak_password(self):
        """Test that weak password fails."""
        data = {
            "token": "abc123def456",
            "password": "weak",
            "password_confirm": "weak",
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(**data)
        assert "password" in str(exc_info.value).lower()


class TestChangePasswordRequest:
    """Test ChangePasswordRequest schema."""

    def test_valid_change_password(self):
        """Test valid change password request."""
        data = {
            "current_password": "OldP@ssw0rd",
            "new_password": "NewP@ssw0rd",
            "new_password_confirm": "NewP@ssw0rd",
        }
        change = ChangePasswordRequest(**data)
        assert change.current_password == "OldP@ssw0rd"
        assert change.new_password == "NewP@ssw0rd"

    def test_change_password_new_same_as_current(self):
        """Test that new password same as current fails."""
        data = {
            "current_password": "SameP@ssw0rd",
            "new_password": "SameP@ssw0rd",
            "new_password_confirm": "SameP@ssw0rd",
        }
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(**data)
        assert "different" in str(exc_info.value).lower()

    def test_change_password_new_passwords_dont_match(self):
        """Test that mismatched new passwords fail."""
        data = {
            "current_password": "OldP@ssw0rd",
            "new_password": "NewP@ssw0rd",
            "new_password_confirm": "DifferentP@ssw0rd",
        }
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(**data)
        assert "do not match" in str(exc_info.value).lower()


class TestEmailVerificationRequest:
    """Test EmailVerificationRequest schema."""

    def test_valid_email_verification(self):
        """Test valid email verification request."""
        data = {"token": "abc123def456"}
        verify = EmailVerificationRequest(**data)
        assert verify.token == "abc123def456"

    def test_email_verification_missing_token(self):
        """Test that request without token fails."""
        with pytest.raises(ValidationError) as exc_info:
            EmailVerificationRequest(**{})
        assert "token" in str(exc_info.value)


class TestLogoutRequest:
    """Test LogoutRequest schema."""

    def test_logout_with_refresh_token(self):
        """Test logout with refresh token."""
        data = {"refresh_token": "eyJ0eXAiOiJKV1QiLCJh..."}
        logout = LogoutRequest(**data)
        assert logout.refresh_token == "eyJ0eXAiOiJKV1QiLCJh..."
        assert logout.all_devices is False

    def test_logout_all_devices(self):
        """Test logout with all_devices flag."""
        data = {"all_devices": True}
        logout = LogoutRequest(**data)
        assert logout.all_devices is True
        assert logout.refresh_token is None

    def test_logout_empty(self):
        """Test logout with empty request."""
        logout = LogoutRequest(**{})
        assert logout.refresh_token is None
        assert logout.all_devices is False


class TestAuthStatusResponse:
    """Test AuthStatusResponse schema."""

    def test_authenticated_status(self):
        """Test authenticated status response."""
        data = {
            "authenticated": True,
            "user_id": 123,
            "username": "john_doe",
            "role": "admin",
            "session_expires_at": datetime(2025, 11, 24, 15, 0),
        }
        status = AuthStatusResponse(**data)
        assert status.authenticated is True
        assert status.user_id == 123
        assert status.username == "john_doe"
        assert status.role == "admin"

    def test_unauthenticated_status(self):
        """Test unauthenticated status response."""
        data = {"authenticated": False}
        status = AuthStatusResponse(**data)
        assert status.authenticated is False
        assert status.user_id is None
        assert status.username is None
        assert status.role is None

    def test_auth_status_missing_authenticated(self):
        """Test that response without authenticated field fails."""
        with pytest.raises(ValidationError) as exc_info:
            AuthStatusResponse(**{})
        assert "authenticated" in str(exc_info.value)

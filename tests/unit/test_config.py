"""Unit tests for configuration management (app/core/config.py).

This module tests the Pydantic Settings-based configuration system:
- Environment variable loading and validation
- Default values and computed properties
- Field validators (SECRET_KEY strength, DEBUG mode, CORS)
- Helper methods (get_sqlalchemy_database_uri, is_production, etc.)
- Settings singleton pattern

Test Coverage:
- Valid configuration scenarios
- Invalid configuration detection
- Security validation (weak keys, DEBUG in production)
- Computed properties and parsing (CORS lists, database URI)
- Environment-specific behavior
"""

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_settings_from_env(monkeypatch):
    """Isolate Settings from .env file during tests.

    This fixture ensures tests use only explicitly set environment variables
    and don't load from .env file. Applied automatically to all tests in this module.
    """
    # Temporarily disable .env file loading for Settings
    original_config = Settings.model_config
    Settings.model_config = SettingsConfigDict(
        env_file=None,  # Don't load from .env
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Clear the LRU cache to ensure fresh Settings instances
    get_settings.cache_clear()

    yield

    # Restore original config
    Settings.model_config = original_config
    get_settings.cache_clear()


class TestSettings:
    """Tests for Settings class configuration validation."""

    def test_settings_with_required_fields(self, monkeypatch):
        """Test Settings initialization with all required fields."""
        # Set minimum required environment variables
        monkeypatch.setenv("SECRET_KEY", "a" * 32)  # 32 characters minimum
        monkeypatch.setenv("AUTH_DB_URI", "postgresql://user:pass@localhost:5432/db")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.SECRET_KEY == "a" * 32
        assert settings.AUTH_DB_URI == "postgresql://user:pass@localhost:5432/db"
        assert settings.APP_NAME == "Privasee BI SaaS"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False

    def test_settings_with_minimal_config(self, monkeypatch):
        """Test Settings with only SECRET_KEY (AUTH_DB_URI constructed from components)."""
        # Clear .env file loading to use only monkeypatch values
        monkeypatch.delenv("AUTH_DB_URI", raising=False)

        monkeypatch.setenv("SECRET_KEY", "b" * 32)
        monkeypatch.setenv("AUTH_DB_USER", "test_user")
        monkeypatch.setenv("AUTH_DB_PASSWORD", "test_pass")
        monkeypatch.setenv("AUTH_DB_NAME", "test_db")
        monkeypatch.setenv("AUTH_DB_HOST", "localhost")
        monkeypatch.setenv("AUTH_DB_PORT", "5432")

        # Clear cache to force reload
        get_settings.cache_clear()
        settings = Settings()  # type: ignore[call-arg]

        # Verify computed URI from components
        expected_uri = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert settings.get_sqlalchemy_database_uri() == expected_uri

    def test_settings_missing_secret_key(self, monkeypatch):
        """Test Settings raises ValidationError when SECRET_KEY is missing."""
        # Remove SECRET_KEY from environment and disable .env loading
        monkeypatch.delenv("SECRET_KEY", raising=False)
        # Also need to patch the .env file reading
        monkeypatch.setattr(
            "pydantic_settings.sources.DotEnvSettingsSource.__call__",
            lambda *args, **kwargs: {},
        )

        # Clear cache to force reload
        get_settings.cache_clear()

        with pytest.raises(ValidationError) as exc_info:
            Settings()  # type: ignore[call-arg]

        # Verify error is for SECRET_KEY field
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("SECRET_KEY",) for error in errors)

    def test_secret_key_too_short(self, monkeypatch):
        """Test Settings rejects SECRET_KEY shorter than 32 characters."""
        monkeypatch.setenv("SECRET_KEY", "tooshort")

        with pytest.raises(ValidationError) as exc_info:
            Settings()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        # Check for SECRET_KEY validation error
        secret_key_errors = [e for e in errors if "SECRET_KEY" in str(e["loc"])]
        assert len(secret_key_errors) > 0

    def test_secret_key_weak_pattern(self, monkeypatch):
        """Test Settings rejects weak SECRET_KEY patterns."""
        weak_keys = [
            "changemechangemechangemechangemechangeme",  # Contains 'changeme' (40 chars)
            "secretsecretsecretsecretsecretsecret",  # Contains 'secret' (36 chars)
            "passwordpasswordpasswordpasswordpass",  # Contains 'password' (37 chars)
            "12345678901234567890123456789012345678",  # Contains '12345' (38 chars)
        ]

        for weak_key in weak_keys:
            # Clear cache before each test
            get_settings.cache_clear()
            monkeypatch.setenv("SECRET_KEY", weak_key)

            with pytest.raises(ValidationError) as exc_info:
                Settings()  # type: ignore[call-arg]

            # Verify error mentions weak pattern
            error_msg = str(exc_info.value)
            assert "weak patterns" in error_msg.lower() or "weak" in error_msg.lower()

    def test_debug_mode_in_production(self, monkeypatch):
        """Test Settings rejects DEBUG=True in production environment."""
        monkeypatch.setenv("SECRET_KEY", "c" * 32)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "true")

        with pytest.raises(ValidationError) as exc_info:
            Settings()  # type: ignore[call-arg]

        error_msg = str(exc_info.value)
        assert "production" in error_msg.lower()

    def test_wildcard_cors_in_production(self, monkeypatch):
        """Test Settings rejects wildcard CORS origins in production."""
        monkeypatch.setenv("SECRET_KEY", "d" * 32)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "*")

        with pytest.raises(ValidationError) as exc_info:
            Settings()  # type: ignore[call-arg]

        error_msg = str(exc_info.value)
        assert "wildcard" in error_msg.lower()

    def test_cors_origins_parsing(self, monkeypatch):
        """Test CORS origins string is correctly parsed into list."""
        monkeypatch.setenv("SECRET_KEY", "e" * 32)
        monkeypatch.setenv(
            "CORS_ORIGINS", "http://localhost:3000, https://example.com, https://api.example.com"
        )

        settings = Settings()  # type: ignore[call-arg]
        origins = settings.get_cors_origins_list()

        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins
        assert "https://api.example.com" in origins

    def test_cors_methods_parsing(self, monkeypatch):
        """Test CORS methods string is correctly parsed into list."""
        monkeypatch.setenv("SECRET_KEY", "f" * 32)
        monkeypatch.setenv("CORS_METHODS", "GET, POST, PUT, DELETE")

        settings = Settings()  # type: ignore[call-arg]
        methods = settings.get_cors_methods_list()

        assert len(methods) == 4
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_cors_headers_parsing(self, monkeypatch):
        """Test CORS headers string is correctly parsed into list."""
        monkeypatch.setenv("SECRET_KEY", "g" * 32)
        monkeypatch.setenv("CORS_ALLOW_HEADERS", "Content-Type, Authorization, X-Custom-Header")

        settings = Settings()  # type: ignore[call-arg]
        headers = settings.get_cors_headers_list()

        assert len(headers) == 3
        assert "Content-Type" in headers
        assert "Authorization" in headers
        assert "X-Custom-Header" in headers

    def test_database_port_validation(self, monkeypatch):
        """Test AUTH_DB_PORT rejects invalid port numbers."""
        monkeypatch.setenv("SECRET_KEY", "h" * 32)
        monkeypatch.setenv("AUTH_DB_PORT", "99999")  # Invalid port > 65535

        with pytest.raises(ValidationError) as exc_info:
            Settings()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        port_errors = [e for e in errors if "AUTH_DB_PORT" in str(e["loc"])]
        assert len(port_errors) > 0

    def test_sqlalchemy_pool_size_validation(self, monkeypatch):
        """Test SQLALCHEMY_POOL_SIZE rejects invalid values."""
        monkeypatch.setenv("SECRET_KEY", "i" * 32)
        monkeypatch.setenv("SQLALCHEMY_POOL_SIZE", "0")  # Invalid: must be >= 1

        with pytest.raises(ValidationError) as exc_info:
            Settings()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        pool_errors = [e for e in errors if "SQLALCHEMY_POOL_SIZE" in str(e["loc"])]
        assert len(pool_errors) > 0


class TestSettingsComputedProperties:
    """Tests for Settings computed properties and helper methods."""

    def test_get_sqlalchemy_database_uri_explicit(self, monkeypatch):
        """Test get_sqlalchemy_database_uri returns explicit AUTH_DB_URI if provided."""
        monkeypatch.setenv("SECRET_KEY", "j" * 32)
        monkeypatch.setenv("AUTH_DB_URI", "postgresql://explicit:uri@host:5432/db")

        settings = Settings()  # type: ignore[call-arg]
        uri = settings.get_sqlalchemy_database_uri()

        assert uri == "postgresql://explicit:uri@host:5432/db"

    def test_get_sqlalchemy_database_uri_constructed(self, monkeypatch):
        """Test get_sqlalchemy_database_uri constructs URI from components."""
        # Clear AUTH_DB_URI to force construction from components
        monkeypatch.delenv("AUTH_DB_URI", raising=False)

        monkeypatch.setenv("SECRET_KEY", "k" * 32)
        monkeypatch.setenv("AUTH_DB_USER", "testuser")
        monkeypatch.setenv("AUTH_DB_PASSWORD", "testpass")
        monkeypatch.setenv("AUTH_DB_NAME", "testdb")
        monkeypatch.setenv("AUTH_DB_HOST", "testhost")
        monkeypatch.setenv("AUTH_DB_PORT", "5433")

        # Clear cache to force reload
        get_settings.cache_clear()
        settings = Settings()  # type: ignore[call-arg]
        uri = settings.get_sqlalchemy_database_uri()

        assert uri == "postgresql://testuser:testpass@testhost:5433/testdb"

    def test_is_development(self, monkeypatch):
        """Test is_development returns True for development environment."""
        monkeypatch.setenv("SECRET_KEY", "l" * 32)
        monkeypatch.setenv("ENVIRONMENT", "development")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.is_development() is True
        assert settings.is_production() is False
        assert settings.is_testing() is False

    def test_is_production(self, monkeypatch):
        """Test is_production returns True for production environment."""
        monkeypatch.setenv("SECRET_KEY", "m" * 32)
        monkeypatch.setenv("ENVIRONMENT", "production")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.is_development() is False
        assert settings.is_production() is True
        assert settings.is_testing() is False

    def test_is_testing(self, monkeypatch):
        """Test is_testing returns True when TESTING flag is set."""
        monkeypatch.setenv("SECRET_KEY", "n" * 32)
        monkeypatch.setenv("TESTING", "true")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.is_testing() is True


class TestGetSettingsSingleton:
    """Tests for get_settings() singleton pattern."""

    def test_get_settings_returns_same_instance(self, monkeypatch):
        """Test get_settings() returns the same instance (singleton)."""
        monkeypatch.setenv("SECRET_KEY", "o" * 32)

        # Clear LRU cache to ensure fresh start
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Verify same instance
        assert settings1 is settings2

    def test_get_settings_caches_result(self, monkeypatch):
        """Test get_settings() uses cache (doesn't reload from env)."""
        monkeypatch.setenv("SECRET_KEY", "p" * 32)
        monkeypatch.setenv("APP_NAME", "Original Name")

        # Clear cache and get settings
        get_settings.cache_clear()
        settings1 = get_settings()
        original_name = settings1.APP_NAME

        # Change environment variable
        monkeypatch.setenv("APP_NAME", "Changed Name")

        # Get settings again (should return cached instance)
        settings2 = get_settings()

        # Verify still using cached value (not reloaded)
        assert settings2.APP_NAME == original_name
        assert settings1 is settings2


class TestSettingsEnvironmentSpecific:
    """Tests for environment-specific configuration behavior."""

    def test_development_defaults(self, monkeypatch):
        """Test development environment has correct defaults."""
        monkeypatch.setenv("SECRET_KEY", "q" * 32)
        monkeypatch.setenv("ENVIRONMENT", "development")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False  # Still False by default, user must enable
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "text"
        assert settings.SQLALCHEMY_ECHO is False

    def test_production_configuration(self, monkeypatch):
        """Test production environment configuration."""
        monkeypatch.setenv("SECRET_KEY", "r" * 32)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "WARNING"
        assert settings.LOG_FORMAT == "json"

    def test_staging_configuration(self, monkeypatch):
        """Test staging environment configuration."""
        monkeypatch.setenv("SECRET_KEY", "s" * 32)
        monkeypatch.setenv("ENVIRONMENT", "staging")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.ENVIRONMENT == "staging"
        assert settings.is_development() is False
        assert settings.is_production() is False

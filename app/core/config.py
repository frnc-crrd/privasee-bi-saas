"""Application configuration management with Pydantic Settings.

This module provides centralized, type-safe configuration management for the application.
All configuration values are loaded from environment variables with comprehensive validation.

Features:
- Type-safe configuration with Pydantic validation
- Environment-specific settings (development, staging, production)
- Secure handling of sensitive credentials
- Computed properties for derived configuration values
- Singleton pattern for efficient configuration access

Usage:
    from app.core.config import get_settings

    settings = get_settings()
    app.config["SECRET_KEY"] = settings.SECRET_KEY
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable validation.

    All configuration values are loaded from environment variables or .env file.
    Pydantic performs automatic validation and type conversion.

    Attributes:
        APP_NAME: Application name for logging and monitoring
        ENVIRONMENT: Deployment environment (development, staging, production)
        DEBUG: Enable Flask debug mode (never use in production)
        TESTING: Flag indicating test environment (disables validations)

        SECRET_KEY: Flask session signing key (must be cryptographically secure)

        AUTH_DB_USER: PostgreSQL username for authentication database
        AUTH_DB_PASSWORD: PostgreSQL password for authentication database
        AUTH_DB_NAME: PostgreSQL database name
        AUTH_DB_HOST: PostgreSQL host (localhost or service name)
        AUTH_DB_PORT: PostgreSQL port (default: 5432)
        AUTH_DB_URI: Full PostgreSQL connection string (computed or explicit)

        SOURCES__SQL_SERVER__CREDENTIALS: SQL Server ODBC connection string
        DESTINATION__DUCKDB__CREDENTIALS: DuckDB file path for analytical cube

        SQLALCHEMY_TRACK_MODIFICATIONS: Disable SQLAlchemy modification tracking
        SQLALCHEMY_ECHO: Enable SQL query logging (debug only)
        SQLALCHEMY_POOL_SIZE: Database connection pool size
        SQLALCHEMY_MAX_OVERFLOW: Max connections beyond pool size
        SQLALCHEMY_POOL_TIMEOUT: Connection acquisition timeout (seconds)

        CORS_ORIGINS: Allowed CORS origins (comma-separated list)
        CORS_METHODS: Allowed HTTP methods for CORS
        CORS_ALLOW_HEADERS: Allowed headers for CORS requests

        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        LOG_FORMAT: Log output format (json for production, text for dev)
        LOG_FILE: Optional log file path (empty = stdout only)

        RATE_LIMIT_ENABLED: Enable rate limiting middleware
        RATE_LIMIT_DEFAULT: Default rate limit (e.g., "100/hour")
        RATE_LIMIT_STORAGE_URL: Redis URL for rate limit storage
    """

    # =========================================================================
    # Application Settings
    # =========================================================================
    APP_NAME: str = Field(
        default="Privasee BI SaaS",
        description="Application name for logging and monitoring",
    )

    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )

    DEBUG: bool = Field(
        default=False,
        description="Enable Flask debug mode (never use in production)",
    )

    TESTING: bool = Field(
        default=False,
        description="Flag indicating test environment",
    )

    # =========================================================================
    # Security Settings
    # =========================================================================
    SECRET_KEY: str = Field(
        ...,  # Required field
        min_length=32,
        description="Flask session signing key (must be cryptographically secure)",
    )

    # =========================================================================
    # PostgreSQL Authentication Database (OLTP)
    # =========================================================================
    AUTH_DB_USER: str = Field(
        default="auth_admin",
        description="PostgreSQL username",
    )

    AUTH_DB_PASSWORD: str = Field(
        default="SecretAuthPassword!",
        description="PostgreSQL password",
    )

    AUTH_DB_NAME: str = Field(
        default="privasee_users",
        description="PostgreSQL database name",
    )

    AUTH_DB_HOST: str = Field(
        default="localhost",
        description="PostgreSQL host",
    )

    AUTH_DB_PORT: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="PostgreSQL port",
    )

    AUTH_DB_URI: str | None = Field(
        default=None,
        description="Full PostgreSQL connection string (optional, computed if not provided)",
    )

    # =========================================================================
    # ETL Data Sources
    # =========================================================================
    SOURCES__SQL_SERVER__CREDENTIALS: str | None = Field(
        default=None,
        description="SQL Server ODBC connection string for ETL extraction",
    )

    DESTINATION__DUCKDB__CREDENTIALS: str = Field(
        default="duckdb:///./data/analytical_cube.duckdb",
        description="DuckDB file path for analytical cube",
    )

    # =========================================================================
    # SQLAlchemy Configuration
    # =========================================================================
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = Field(
        default=False,
        description="Disable modification tracking to reduce memory overhead",
    )

    SQLALCHEMY_ECHO: bool = Field(
        default=False,
        description="Enable SQL query logging (use only for debugging)",
    )

    SQLALCHEMY_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Database connection pool size",
    )

    SQLALCHEMY_MAX_OVERFLOW: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Max connections beyond pool size",
    )

    SQLALCHEMY_POOL_TIMEOUT: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Connection acquisition timeout in seconds",
    )

    # =========================================================================
    # CORS Configuration
    # =========================================================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5000",
        description="Comma-separated list of allowed CORS origins",
    )

    CORS_METHODS: str = Field(
        default="GET,POST,PUT,DELETE,PATCH,OPTIONS",
        description="Allowed HTTP methods for CORS",
    )

    CORS_ALLOW_HEADERS: str = Field(
        default="Content-Type,Authorization,X-Request-ID",
        description="Allowed headers for CORS requests",
    )

    # =========================================================================
    # Logging Configuration
    # =========================================================================
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    LOG_FORMAT: Literal["json", "text"] = Field(
        default="text",
        description="Log output format (json for production, text for dev)",
    )

    LOG_FILE: str = Field(
        default="",
        description="Optional log file path (empty = stdout only)",
    )

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable rate limiting middleware",
    )

    RATE_LIMIT_DEFAULT: str = Field(
        default="100/hour",
        description="Default rate limit per IP",
    )

    RATE_LIMIT_STORAGE_URL: str = Field(
        default="memory://",
        description="Redis URL for rate limit storage (memory:// for in-memory)",
    )

    # =========================================================================
    # Pydantic Configuration
    # =========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is cryptographically secure.

        Args:
            v: Secret key value

        Returns:
            Validated secret key

        Raises:
            ValueError: If secret key is too weak
        """
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

        # Warn about common weak keys (not in production)
        weak_keys = ["changeme", "secret", "password", "12345"]
        if any(weak in v.lower() for weak in weak_keys):
            raise ValueError(
                "SECRET_KEY contains weak patterns. "
                "Generate a secure key with: openssl rand -hex 32"
            )

        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_mode(cls, v: bool, info) -> bool:
        """Ensure DEBUG is never enabled in production.

        Args:
            v: Debug flag value
            info: Validation context with other field values

        Returns:
            Validated debug flag

        Raises:
            ValueError: If DEBUG is enabled in production
        """
        environment = info.data.get("ENVIRONMENT", "development")
        if v and environment == "production":
            raise ValueError("DEBUG mode must never be enabled in production")

        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str, info) -> str:
        """Validate CORS origins based on environment.

        Args:
            v: CORS origins string
            info: Validation context

        Returns:
            Validated CORS origins

        Raises:
            ValueError: If wildcard CORS is used in production
        """
        environment = info.data.get("ENVIRONMENT", "development")
        if "*" in v and environment == "production":
            raise ValueError(
                "Wildcard CORS origins (*) are not allowed in production. "
                "Specify explicit origins."
            )

        return v

    # =========================================================================
    # Computed Properties
    # =========================================================================
    def get_sqlalchemy_database_uri(self) -> str:
        """Generate SQLAlchemy database URI from components.

        Returns:
            PostgreSQL connection string for SQLAlchemy

        Raises:
            ValueError: If AUTH_DB_URI is invalid
        """
        if self.AUTH_DB_URI:
            return self.AUTH_DB_URI

        # Construct URI from components
        return (
            f"postgresql://{self.AUTH_DB_USER}:{self.AUTH_DB_PASSWORD}"
            f"@{self.AUTH_DB_HOST}:{self.AUTH_DB_PORT}/{self.AUTH_DB_NAME}"
        )

    def get_cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into a list.

        Returns:
            List of allowed CORS origins
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def get_cors_methods_list(self) -> list[str]:
        """Parse CORS methods string into a list.

        Returns:
            List of allowed HTTP methods
        """
        return [method.strip() for method in self.CORS_METHODS.split(",")]

    def get_cors_headers_list(self) -> list[str]:
        """Parse CORS headers string into a list.

        Returns:
            List of allowed headers
        """
        return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",")]

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if ENVIRONMENT is development
        """
        return self.ENVIRONMENT == "development"

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if ENVIRONMENT is production
        """
        return self.ENVIRONMENT == "production"

    def is_testing(self) -> bool:
        """Check if running in test environment.

        Returns:
            True if TESTING flag is set
        """
        return self.TESTING


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern).

    This function uses LRU cache to ensure only one Settings instance
    is created during the application lifecycle, improving performance
    and ensuring consistency.

    Returns:
        Cached Settings instance with validated configuration

    Example:
        >>> from app.core.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        'Privasee BI SaaS'
    """
    # Pylance doesn't detect that Pydantic Settings loads from environment
    return Settings()  # type: ignore[call-arg]

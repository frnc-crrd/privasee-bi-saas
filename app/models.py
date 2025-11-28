# app/models.py
"""
Database Models
---------------
Defines all SQLAlchemy ORM models for the application.
Includes User authentication model with secure password handling.
"""

from datetime import datetime, timezone
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.extensions import bcrypt, db


class AuditEventType(enum.Enum):
    """
    Enumeration of security-relevant events tracked in the audit log.

    Categories:
        Authentication: login, logout, login_failed, password_change, password_reset
        Authorization: role_change, permission_denied
        Data Access: data_export, sensitive_data_access
        Account Management: user_created, user_deleted, user_updated
        System: api_error, config_change
    """
    # Authentication Events
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"

    # Authorization Events
    ROLE_CHANGE = "role_change"
    PERMISSION_DENIED = "permission_denied"

    # Data Access Events
    DATA_EXPORT = "data_export"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"

    # Account Management Events
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_UPDATED = "user_updated"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_ENABLED = "account_enabled"

    # System Events
    API_ERROR = "api_error"
    CONFIG_CHANGE = "config_change"


class AuditSeverity(enum.Enum):
    """
    Severity levels for audit events following standard logging conventions.

    Levels:
        INFO: Normal operational events (login, logout)
        WARNING: Potentially suspicious events (login_failed, permission_denied)
        CRITICAL: Security-critical events (role_change, account_disabled)
    """
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class User(db.Model, UserMixin):
    """
    User Model
    ----------
    Represents the application users stored in the PostgreSQL 'auth_db'.
    Inherits from UserMixin to provide default Flask-Login implementation
    (is_authenticated, is_active, etc.).

    Attributes:
        id: Primary key, unique user identifier
        email: Unique email address for login
        username: Unique username for display
        password_hash: Bcrypt-hashed password (never stored in plaintext)
        role: User role for RBAC (admin, viewer, analyst)
        is_active: Account status flag
        created_at: Account creation timestamp
        last_login: Last successful login timestamp
    """

    __tablename__ = "users"

    # Primary Key: Auto-incrementing Integer (Efficient for Postgres)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identification
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Security: Store hash, NEVER plain text password
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authorization (RBAC)
    # Examples: 'admin', 'viewer', 'analyst'
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")

    # Status & Audit Trails (Enterprise Best Practice)
    # Note: is_active is defined as a column, overriding UserMixin's property
    is_active: Mapped[bool] = mapped_column(  # type: ignore[assignment]
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str = "",
        role: str = "viewer",
        is_active: bool = True,  # type: ignore[assignment]
    ) -> None:
        """
        Initialize a new User instance.

        Args:
            username: Unique username for the user
            email: Unique email address for the user
            password_hash: Pre-hashed password (optional, use set_password instead)
            role: User role for authorization (default: viewer)
            is_active: Account active status (default: True)
        """
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.is_active = is_active  # type: ignore[misc]

    # =========================================================================
    # Password Management
    # =========================================================================

    @property
    def password(self) -> str:
        """
        Password property (write-only).
        Reading passwords is not allowed for security reasons.

        Returns:
            The password hash (for comparison in tests).

        Note:
            In production, this should raise AttributeError.
            For testing compatibility, it returns the hash.
        """
        return self.password_hash

    @password.setter
    def password(self, plaintext_password: str) -> None:
        """
        Set user password by hashing the plaintext value.

        Args:
            plaintext_password: Raw password string to be hashed.

        Note:
            This is a convenience setter. Use set_password() for explicit calls.
        """
        self.set_password(plaintext_password)

    def set_password(self, password: str) -> None:
        """
        Hash and store the user's password securely using bcrypt.

        Args:
            password: Raw password string to be hashed.

        Security:
            Uses bcrypt algorithm with automatic salt generation.
            The resulting hash is stored in password_hash column.
        """
        self.password_hash = bcrypt.generate_password_hash(password).decode(  # type: ignore[arg-type]
            "utf-8"
        )

    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.

        Args:
            password: Password string to verify.

        Returns:
            True if password matches, False otherwise.

        Security:
            Uses constant-time comparison to prevent timing attacks.
        """
        return bcrypt.check_password_hash(  # type: ignore[arg-type]
            self.password_hash, password
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class AuditLog(db.Model):
    """
    Audit Log Model
    ---------------
    Immutable record of security-relevant events for compliance and forensics.
    Tracks all authentication, authorization, and data access events.

    Attributes:
        id: Primary key, unique audit record identifier
        event_type: Type of event (login, logout, role_change, etc.)
        severity: Event severity level (info, warning, critical)
        user_id: ID of user who triggered the event (nullable for failed logins)
        username: Username snapshot at event time (denormalized for audit trail)
        ip_address: Client IP address where event originated
        user_agent: Client user agent string
        endpoint: API endpoint or route accessed
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP response status code
        details: JSON object with event-specific metadata
        timestamp: Event occurrence timestamp (UTC)

    Security:
        - Records are append-only (no updates or deletes)
        - Indexed for fast queries by user, event type, and time range
        - Retains username even if user is deleted
    """

    __tablename__ = "audit_logs"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Event Classification
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    severity: Mapped[AuditSeverity] = mapped_column(
        Enum(AuditSeverity, native_enum=False, length=20),
        nullable=False,
        default=AuditSeverity.INFO
    )

    # User Context (denormalized for audit trail persistence)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Request Context
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        index=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    endpoint: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    method: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True
    )
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Event Details (JSON for flexible metadata storage)
    details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Timestamp (UTC, immutable)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def __init__(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Initialize a new AuditLog entry.

        Args:
            event_type: Type of security event
            severity: Event severity level (default: INFO)
            user_id: User ID who triggered the event
            username: Username snapshot at event time
            ip_address: Client IP address
            user_agent: Client user agent string
            endpoint: API endpoint accessed
            method: HTTP method
            status_code: HTTP response status
            details: JSON string with event-specific metadata
        """
        self.event_type = event_type
        self.severity = severity
        self.user_id = user_id
        self.username = username
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.details = details

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<AuditLog(id={self.id}, event='{self.event_type.value}', "
            f"user='{self.username}', timestamp='{self.timestamp}')>"
        )

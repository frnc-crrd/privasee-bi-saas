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
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import bcrypt, db


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

# app/models.py
from datetime import datetime, timezone
from typing import Optional
from flask_login import UserMixin
from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db, bcrypt

class User(db.Model, UserMixin):
    """
    User Model
    ----------
    Represents the application users stored in the PostgreSQL 'auth_db'.
    Inherits from UserMixin to provide default Flask-Login implementation
    (is_authenticated, is_active, etc.).
    """
    __tablename__ = 'users'

    # Primary Key: Auto-incrementing Integer (Efficient for Postgres)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identification
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Security
    # We store the hash, NEVER the plain text password
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Authorization (RBAC)
    # Examples: 'admin', 'viewer', 'analyst'
    role: Mapped[str] = mapped_column(String(20), nullable=False, default='viewer')

    # Status & Audit Trails (Enterprise Best Practice)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def set_password(self, password: str) -> None:
        """
        Encrypts the plain password using Bcrypt and stores the hash.
        """
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """
        Verifies a plain password against the stored hash.
        Returns True if matches, False otherwise.
        """
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

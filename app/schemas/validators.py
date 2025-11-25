"""Custom validators for Pydantic schemas.

This module provides reusable field validators for common data validation:
- Password strength validation
- Email format validation (extended)
- Username validation
- Role validation
- Date range validation

All validators raise ValueError with descriptive messages on validation failure.

Usage:
    from pydantic import BaseModel, field_validator
    from app.schemas.validators import validate_password_strength

    class RegisterRequest(BaseModel):
        password: str

        @field_validator("password")
        @classmethod
        def validate_password(cls, v: str) -> str:
            return validate_password_strength(v)
"""

import re
from datetime import datetime
from typing import Optional


def validate_password_strength(
    password: str,
    min_length: int = 8,
    max_length: int = 128,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = True,
) -> str:
    """Validate password strength against security requirements.

    Args:
        password: Password to validate
        min_length: Minimum password length (default: 8)
        max_length: Maximum password length (default: 128)
        require_uppercase: Require at least one uppercase letter
        require_lowercase: Require at least one lowercase letter
        require_digit: Require at least one digit
        require_special: Require at least one special character

    Returns:
        The validated password (unchanged)

    Raises:
        ValueError: If password doesn't meet strength requirements

    Example:
        >>> validate_password_strength("MyP@ssw0rd")
        'MyP@ssw0rd'
        >>> validate_password_strength("weak")
        ValueError: Password must be at least 8 characters long
    """
    if not password:
        raise ValueError("Password is required")

    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters long")

    if len(password) > max_length:
        raise ValueError(f"Password must not exceed {max_length} characters")

    if require_uppercase and not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if require_lowercase and not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if require_digit and not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    if require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/`~;']", password):
        raise ValueError("Password must contain at least one special character")

    # Check for common weak patterns
    common_patterns = [
        r"^password",
        r"^123+",
        r"^abc+",
        r"qwerty",
        r"admin",
    ]

    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            raise ValueError(f"Password contains common weak pattern: {pattern}")

    return password


def validate_username(
    username: str,
    min_length: int = 3,
    max_length: int = 30,
    allow_special: bool = False,
) -> str:
    """Validate username format and length.

    Usernames must:
    - Be between min_length and max_length characters
    - Start with a letter
    - Contain only alphanumeric characters, underscores, and hyphens (optionally)

    Args:
        username: Username to validate
        min_length: Minimum username length (default: 3)
        max_length: Maximum username length (default: 30)
        allow_special: Allow special characters beyond underscore/hyphen

    Returns:
        The validated username (unchanged)

    Raises:
        ValueError: If username doesn't meet format requirements

    Example:
        >>> validate_username("john_doe")
        'john_doe'
        >>> validate_username("ab")
        ValueError: Username must be at least 3 characters long
    """
    if not username:
        raise ValueError("Username is required")

    if len(username) < min_length:
        raise ValueError(f"Username must be at least {min_length} characters long")

    if len(username) > max_length:
        raise ValueError(f"Username must not exceed {max_length} characters")

    # Must start with a letter
    if not username[0].isalpha():
        raise ValueError("Username must start with a letter")

    # Check allowed characters
    if allow_special:
        # Allow any printable characters except whitespace
        if not username.isprintable() or any(c.isspace() for c in username):
            raise ValueError("Username cannot contain whitespace or non-printable characters")
    else:
        # Only alphanumeric, underscore, and hyphen
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")

    # Check for reserved usernames
    reserved_usernames = [
        "admin",
        "administrator",
        "root",
        "system",
        "support",
        "help",
        "api",
        "null",
        "undefined",
    ]

    if username.lower() in reserved_usernames:
        raise ValueError(f"Username '{username}' is reserved and cannot be used")

    return username


def validate_email_format(email: str) -> str:
    """Validate email format with additional checks beyond Pydantic's EmailStr.

    Performs additional validation:
    - Checks for disposable email domains
    - Validates domain structure
    - Checks for common typos

    Args:
        email: Email address to validate

    Returns:
        The validated email (lowercase)

    Raises:
        ValueError: If email format is invalid

    Example:
        >>> validate_email_format("user@example.com")
        'user@example.com'
        >>> validate_email_format("invalid@")
        ValueError: Invalid email format
    """
    if not email:
        raise ValueError("Email is required")

    # Convert to lowercase for consistency
    email = email.lower().strip()

    # Basic format check (Pydantic EmailStr does this, but we do it explicitly)
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")

    # Check for disposable email domains (basic list)
    disposable_domains = [
        "tempmail.com",
        "throwaway.email",
        "guerrillamail.com",
        "10minutemail.com",
        "mailinator.com",
    ]

    domain = email.split("@")[1] if "@" in email else ""
    if domain in disposable_domains:
        raise ValueError("Disposable email addresses are not allowed")

    # Check for common typos in popular domains
    typo_corrections = {
        "gmai.com": "gmail.com",
        "gmial.com": "gmail.com",
        "yahooo.com": "yahoo.com",
        "hotmial.com": "hotmail.com",
    }

    if domain in typo_corrections:
        suggested = typo_corrections[domain]
        raise ValueError(f"Did you mean {email.split('@')[0]}@{suggested}?")

    return email


def validate_role(role: str, allowed_roles: Optional[list[str]] = None) -> str:
    """Validate user role against allowed values.

    Args:
        role: Role to validate
        allowed_roles: List of allowed roles (default: admin, viewer, analyst)

    Returns:
        The validated role (lowercase)

    Raises:
        ValueError: If role is not in allowed_roles

    Example:
        >>> validate_role("admin")
        'admin'
        >>> validate_role("superuser")
        ValueError: Invalid role. Allowed roles: admin, viewer, analyst
    """
    if not role:
        raise ValueError("Role is required")

    if allowed_roles is None:
        allowed_roles = ["admin", "viewer", "analyst"]

    role = role.lower().strip()

    if role not in allowed_roles:
        allowed_str = ", ".join(allowed_roles)
        raise ValueError(f"Invalid role. Allowed roles: {allowed_str}")

    return role


def validate_date_range(
    start_date: datetime,
    end_date: datetime,
    max_range_days: Optional[int] = None,
) -> tuple[datetime, datetime]:
    """Validate date range constraints.

    Args:
        start_date: Range start date
        end_date: Range end date
        max_range_days: Maximum allowed days between start and end (optional)

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        ValueError: If date range is invalid

    Example:
        >>> from datetime import datetime, timedelta
        >>> start = datetime(2025, 1, 1)
        >>> end = datetime(2025, 1, 31)
        >>> validate_date_range(start, end, max_range_days=365)
        (datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 31, 0, 0))
    """
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date")

    if max_range_days is not None:
        delta = (end_date - start_date).days
        if delta > max_range_days:
            raise ValueError(
                f"Date range cannot exceed {max_range_days} days (current: {delta} days)"
            )

    # Check if dates are not too far in the future (sanity check)
    now = datetime.now()
    if start_date > now.replace(year=now.year + 10):
        raise ValueError("Start date cannot be more than 10 years in the future")

    return start_date, end_date


def validate_positive_integer(value: int, field_name: str = "value") -> int:
    """Validate that integer is positive (> 0).

    Args:
        value: Integer to validate
        field_name: Name of field for error message

    Returns:
        The validated integer

    Raises:
        ValueError: If value is not positive

    Example:
        >>> validate_positive_integer(10, "user_id")
        10
        >>> validate_positive_integer(0, "user_id")
        ValueError: user_id must be a positive integer
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def validate_pagination_params(
    page: int = 1,
    per_page: int = 10,
    max_per_page: int = 100,
) -> tuple[int, int]:
    """Validate pagination parameters.

    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        max_per_page: Maximum allowed items per page

    Returns:
        Tuple of (page, per_page)

    Raises:
        ValueError: If pagination parameters are invalid

    Example:
        >>> validate_pagination_params(1, 10)
        (1, 10)
        >>> validate_pagination_params(0, 10)
        ValueError: Page must be at least 1
    """
    if page < 1:
        raise ValueError("Page must be at least 1")

    if per_page < 1:
        raise ValueError("Items per page must be at least 1")

    if per_page > max_per_page:
        raise ValueError(f"Items per page cannot exceed {max_per_page}")

    return page, per_page


def sanitize_string(
    value: str,
    max_length: Optional[int] = None,
    strip_whitespace: bool = True,
    remove_special_chars: bool = False,
) -> str:
    """Sanitize string input by removing unwanted characters.

    Args:
        value: String to sanitize
        max_length: Maximum length (truncate if longer)
        strip_whitespace: Remove leading/trailing whitespace
        remove_special_chars: Remove non-alphanumeric characters (except spaces)

    Returns:
        Sanitized string

    Example:
        >>> sanitize_string("  Hello World!  ", max_length=10)
        'Hello Worl'
    """
    if not value:
        return value

    if strip_whitespace:
        value = value.strip()

    if remove_special_chars:
        # Keep alphanumeric and spaces
        value = re.sub(r"[^a-zA-Z0-9\s]", "", value)

    if max_length is not None and len(value) > max_length:
        value = value[:max_length]

    return value

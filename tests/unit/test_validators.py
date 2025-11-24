"""Unit tests for app.schemas.validators module.

Tests all custom validators for comprehensive coverage.
"""

from datetime import datetime

import pytest

from app.schemas.validators import (
    sanitize_string,
    validate_date_range,
    validate_email_format,
    validate_pagination_params,
    validate_password_strength,
    validate_positive_integer,
    validate_role,
    validate_username,
)


class TestValidatePasswordStrength:
    """Test password strength validation."""

    def test_valid_strong_password(self):
        """Test that strong passwords pass validation."""
        password = "MyP@ssw0rd123"
        result = validate_password_strength(password)
        assert result == password

    def test_password_too_short(self):
        """Test that short passwords fail validation."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("Short1!")

    def test_password_too_long(self):
        """Test that excessively long passwords fail validation."""
        long_password = "A" * 129 + "a1!"
        with pytest.raises(ValueError, match="must not exceed 128 characters"):
            validate_password_strength(long_password)

    def test_password_missing_uppercase(self):
        """Test that passwords without uppercase fail validation."""
        with pytest.raises(ValueError, match="uppercase letter"):
            validate_password_strength("myp@ssw0rd")

    def test_password_missing_lowercase(self):
        """Test that passwords without lowercase fail validation."""
        with pytest.raises(ValueError, match="lowercase letter"):
            validate_password_strength("MYP@SSW0RD")

    def test_password_missing_digit(self):
        """Test that passwords without digits fail validation."""
        with pytest.raises(ValueError, match="digit"):
            validate_password_strength("MyP@ssword")

    def test_password_missing_special_char(self):
        """Test that passwords without special characters fail validation."""
        with pytest.raises(ValueError, match="special character"):
            validate_password_strength("MyPassword123")

    def test_password_common_pattern_password(self):
        """Test that passwords with 'password' pattern fail."""
        with pytest.raises(ValueError, match="common weak pattern"):
            validate_password_strength("Password123!")

    def test_password_common_pattern_123(self):
        """Test that passwords starting with '123' fail."""
        with pytest.raises(ValueError, match="common weak pattern"):
            validate_password_strength("123456Aa!")

    def test_password_empty(self):
        """Test that empty passwords fail validation."""
        with pytest.raises(ValueError, match="required"):
            validate_password_strength("")

    def test_password_custom_min_length(self):
        """Test password validation with custom minimum length."""
        result = validate_password_strength("Ab1!", min_length=4)
        assert result == "Ab1!"

    def test_password_optional_requirements(self):
        """Test password validation with relaxed requirements."""
        result = validate_password_strength(
            "simplepass",
            require_uppercase=False,
            require_digit=False,
            require_special=False,
        )
        assert result == "simplepass"


class TestValidateUsername:
    """Test username validation."""

    def test_valid_username(self):
        """Test that valid usernames pass validation."""
        username = "john_doe"
        result = validate_username(username)
        assert result == username

    def test_username_with_hyphen(self):
        """Test username with hyphens."""
        username = "john-doe"
        result = validate_username(username)
        assert result == username

    def test_username_too_short(self):
        """Test that short usernames fail validation."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            validate_username("ab")

    def test_username_too_long(self):
        """Test that long usernames fail validation."""
        with pytest.raises(ValueError, match="must not exceed 30 characters"):
            validate_username("a" * 31)

    def test_username_starts_with_number(self):
        """Test that usernames starting with numbers fail."""
        with pytest.raises(ValueError, match="must start with a letter"):
            validate_username("1john")

    def test_username_with_spaces(self):
        """Test that usernames with spaces fail."""
        with pytest.raises(ValueError, match="letters, numbers, underscores, and hyphens"):
            validate_username("john doe")

    def test_username_with_special_chars(self):
        """Test that usernames with special characters fail."""
        with pytest.raises(ValueError, match="letters, numbers, underscores, and hyphens"):
            validate_username("john@doe")

    def test_username_reserved_admin(self):
        """Test that reserved username 'admin' fails."""
        with pytest.raises(ValueError, match="reserved"):
            validate_username("admin")

    def test_username_reserved_case_insensitive(self):
        """Test that reserved usernames are case-insensitive."""
        with pytest.raises(ValueError, match="reserved"):
            validate_username("ADMIN")

    def test_username_empty(self):
        """Test that empty usernames fail validation."""
        with pytest.raises(ValueError, match="required"):
            validate_username("")

    def test_username_custom_min_length(self):
        """Test username validation with custom minimum length."""
        result = validate_username("ab", min_length=2)
        assert result == "ab"


class TestValidateEmailFormat:
    """Test email format validation."""

    def test_valid_email(self):
        """Test that valid emails pass validation."""
        email = "user@example.com"
        result = validate_email_format(email)
        assert result == email

    def test_email_lowercase_conversion(self):
        """Test that emails are converted to lowercase."""
        result = validate_email_format("User@Example.COM")
        assert result == "user@example.com"

    def test_email_whitespace_strip(self):
        """Test that whitespace is stripped."""
        result = validate_email_format("  user@example.com  ")
        assert result == "user@example.com"

    def test_email_invalid_format_no_at(self):
        """Test that emails without '@' fail."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email_format("userexample.com")

    def test_email_invalid_format_no_domain(self):
        """Test that emails without domain fail."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email_format("user@")

    def test_email_disposable_domain(self):
        """Test that disposable email domains fail."""
        with pytest.raises(ValueError, match="Disposable email"):
            validate_email_format("user@tempmail.com")

    def test_email_typo_suggestion_gmail(self):
        """Test typo detection for Gmail."""
        with pytest.raises(ValueError, match="Did you mean.*@gmail.com"):
            validate_email_format("user@gmai.com")

    def test_email_empty(self):
        """Test that empty emails fail validation."""
        with pytest.raises(ValueError, match="required"):
            validate_email_format("")


class TestValidateRole:
    """Test role validation."""

    def test_valid_role_admin(self):
        """Test that 'admin' role passes."""
        result = validate_role("admin")
        assert result == "admin"

    def test_valid_role_viewer(self):
        """Test that 'viewer' role passes."""
        result = validate_role("viewer")
        assert result == "viewer"

    def test_valid_role_analyst(self):
        """Test that 'analyst' role passes."""
        result = validate_role("analyst")
        assert result == "analyst"

    def test_role_case_insensitive(self):
        """Test that roles are case-insensitive."""
        result = validate_role("ADMIN")
        assert result == "admin"

    def test_role_whitespace_strip(self):
        """Test that whitespace is stripped."""
        result = validate_role("  admin  ")
        assert result == "admin"

    def test_invalid_role(self):
        """Test that invalid roles fail."""
        with pytest.raises(ValueError, match="Invalid role"):
            validate_role("superuser")

    def test_role_empty(self):
        """Test that empty roles fail validation."""
        with pytest.raises(ValueError, match="required"):
            validate_role("")

    def test_role_custom_allowed_roles(self):
        """Test role validation with custom allowed roles."""
        result = validate_role("moderator", allowed_roles=["admin", "moderator"])
        assert result == "moderator"


class TestValidateDateRange:
    """Test date range validation."""

    def test_valid_date_range(self):
        """Test that valid date ranges pass."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        result = validate_date_range(start, end)
        assert result == (start, end)

    def test_date_range_same_date(self):
        """Test that same start and end dates pass."""
        date = datetime(2025, 1, 1)
        result = validate_date_range(date, date)
        assert result == (date, date)

    def test_date_range_start_after_end(self):
        """Test that start after end fails."""
        start = datetime(2025, 1, 31)
        end = datetime(2025, 1, 1)
        with pytest.raises(ValueError, match="Start date must be before"):
            validate_date_range(start, end)

    def test_date_range_exceeds_max_days(self):
        """Test that ranges exceeding max days fail."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 12, 31)
        with pytest.raises(ValueError, match="cannot exceed 30 days"):
            validate_date_range(start, end, max_range_days=30)

    def test_date_range_far_future(self):
        """Test that dates too far in future fail."""
        start = datetime(2050, 1, 1)
        end = datetime(2050, 1, 31)
        with pytest.raises(ValueError, match="cannot be more than 10 years in the future"):
            validate_date_range(start, end)


class TestValidatePositiveInteger:
    """Test positive integer validation."""

    def test_valid_positive_integer(self):
        """Test that positive integers pass."""
        result = validate_positive_integer(10)
        assert result == 10

    def test_zero_fails(self):
        """Test that zero fails validation."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_integer(0)

    def test_negative_fails(self):
        """Test that negative integers fail."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_positive_integer(-5)

    def test_custom_field_name(self):
        """Test error message with custom field name."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            validate_positive_integer(0, "user_id")


class TestValidatePaginationParams:
    """Test pagination parameter validation."""

    def test_valid_pagination(self):
        """Test that valid pagination parameters pass."""
        result = validate_pagination_params(1, 10)
        assert result == (1, 10)

    def test_pagination_page_zero(self):
        """Test that page 0 fails."""
        with pytest.raises(ValueError, match="Page must be at least 1"):
            validate_pagination_params(0, 10)

    def test_pagination_page_negative(self):
        """Test that negative page fails."""
        with pytest.raises(ValueError, match="Page must be at least 1"):
            validate_pagination_params(-1, 10)

    def test_pagination_per_page_zero(self):
        """Test that per_page 0 fails."""
        with pytest.raises(ValueError, match="Items per page must be at least 1"):
            validate_pagination_params(1, 0)

    def test_pagination_per_page_exceeds_max(self):
        """Test that per_page exceeding max fails."""
        with pytest.raises(ValueError, match="cannot exceed 100"):
            validate_pagination_params(1, 150)

    def test_pagination_custom_max_per_page(self):
        """Test pagination with custom max_per_page."""
        result = validate_pagination_params(1, 50, max_per_page=50)
        assert result == (1, 50)


class TestSanitizeString:
    """Test string sanitization."""

    def test_sanitize_whitespace(self):
        """Test whitespace stripping."""
        result = sanitize_string("  hello world  ")
        assert result == "hello world"

    def test_sanitize_max_length(self):
        """Test max length truncation."""
        result = sanitize_string("hello world", max_length=5)
        assert result == "hello"

    def test_sanitize_remove_special_chars(self):
        """Test special character removal."""
        result = sanitize_string("hello@world!", remove_special_chars=True)
        assert result == "helloworld"

    def test_sanitize_no_strip(self):
        """Test without stripping whitespace."""
        result = sanitize_string("  hello  ", strip_whitespace=False)
        assert result == "  hello  "

    def test_sanitize_empty_string(self):
        """Test empty string sanitization."""
        result = sanitize_string("")
        assert result == ""

    def test_sanitize_combined_options(self):
        """Test sanitization with multiple options."""
        result = sanitize_string(
            "  Hello@World!123  ",
            max_length=10,
            strip_whitespace=True,
            remove_special_chars=True,
        )
        assert result == "HelloWorld"

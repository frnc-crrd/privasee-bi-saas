"""
Unit Tests for User Authentication Model
-----------------------------------------
Tests password hashing, verification, and security measures.
"""

from typing import Any

from app.models import User


def test_password_hashing(db: Any) -> None:
    """
    Test that the password attribute stores a hashed value, not the plaintext.

    Verifies:
        1. Hashed password differs from plaintext
        2. Hash is a non-empty string of sufficient length
    """
    test_password = "secure_password_123"

    # Create a user object (db fixture provides the context)
    user = User(username="hash_tester", email="hash@example.com")

    # Hash the password using the set_password method
    user.set_password(test_password)

    # Assertion 1: The hashed password should not equal the plaintext password
    assert user.password != test_password, "Password hash should differ from plaintext"

    # Assertion 2: The hashed password should be a non-empty string
    assert isinstance(user.password, str), "Password hash should be a string"
    assert len(user.password) > 10, "Password hash should be substantial length"


def test_password_verification(db: Any) -> None:
    """
    Test that the check_password method correctly verifies passwords.

    Verifies:
        1. Correct password passes verification
        2. Incorrect password fails verification
        3. Empty password fails verification
    """
    test_password = "correct_horse_battery_staple"

    # Create and configure user
    user = User(username="verify_tester", email="verify@example.com")
    user.set_password(test_password)

    # Persist user to database
    db.session.add(user)
    db.session.commit()

    # Test case 1: Correct password should pass verification
    assert user.check_password(test_password) is True, "Correct password should verify"

    # Test case 2: Incorrect password should fail verification
    assert user.check_password("wrong_password") is False, "Incorrect password should fail"

    # Test case 3: Empty password check should fail
    assert user.check_password("") is False, "Empty password should fail verification"

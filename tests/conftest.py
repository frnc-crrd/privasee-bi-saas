import logging
from typing import Dict, Any

import pytest
from flask_jwt_extended import create_access_token, create_refresh_token

# Assuming 'app' imports create_app and 'app.extensions' imports the db instance
from app import create_app
from app.extensions import db as _db
from app.models import User

# Note: The 'User' model is often needed by other fixtures, but we only import
# what is strictly necessary here to prevent circular imports if models import db.


@pytest.fixture(scope="session")
def app():
    """
    Creates the test application context, setting the database to in-memory SQLite.
    Scope: session (The app object is created once per test session).
    """
    config_overrides = {
        # Critical setting to ensure Flask is in testing mode
        "TESTING": True,
        # Use an in-memory SQLite database for fast, isolated testing
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        # Other necessary testing configuration
        "SECRET_KEY": "test-key-for-testing-only",
        "WTF_CSRF_ENABLED": False,
    }

    # The create_app function is assumed to be the entry point for app creation
    _app = create_app(config_overrides=config_overrides)

    # Establish application context
    with _app.app_context():
        yield _app


@pytest.fixture(scope="function")
def db(app):
    """
    Initializes and cleans up the database tables for each test.
    Scope: function (Tables are created before each test and cleaned after).
    """
    # Create all tables defined in the models
    _db.create_all()

    yield _db

    # Clean up: remove session and drop all tables
    _db.session.remove()
    _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    A test client for making requests to the application.
    Scope: function (A fresh client is provided for every test function).
    """
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def session_cleanup(app):
    """
    Automatically runs before and after every test function to ensure a clean session.
    This is necessary to clear any data that might have been committed in a test.
    """
    # Reset logging handlers to avoid accumulation
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)  # Reset to default

    # The yield pauses the fixture until the test finishes
    yield

    # Clean logging handlers again
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)


# =========================================================================
# Phase 2 Test Fixtures: Users with different roles
# =========================================================================


@pytest.fixture(scope="function")
def admin_user(app, db):
    """
    Create an admin user for testing admin-only endpoints.
    Scope: function (Fresh user for each test).
    """
    user = User(
        username="admin_test",
        email="admin@test.com",
        role="admin",
        is_active=True
    )
    user.set_password("AdminPass123!")
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)  # Ensure user is fully loaded
    yield user


@pytest.fixture(scope="function")
def analyst_user(app, db):
    """
    Create an analyst user for testing analyst-level endpoints.
    Scope: function (Fresh user for each test).
    """
    user = User(
        username="analyst_test",
        email="analyst@test.com",
        role="analyst",
        is_active=True
    )
    user.set_password("AnalystPass123!")
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    yield user


@pytest.fixture(scope="function")
def viewer_user(app, db):
    """
    Create a viewer user for testing viewer-level endpoints.
    Scope: function (Fresh user for each test).
    """
    user = User(
        username="viewer_test",
        email="viewer@test.com",
        role="viewer",
        is_active=True
    )
    user.set_password("ViewerPass123!")
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    yield user


@pytest.fixture(scope="function")
def inactive_user(app, db):
    """
    Create an inactive user for testing account disabled scenarios.
    Scope: function (Fresh user for each test).
    """
    user = User(
        username="inactive_test",
        email="inactive@test.com",
        role="viewer",
        is_active=False
    )
    user.set_password("InactivePass123!")
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    yield user


# =========================================================================
# Phase 2 Test Fixtures: JWT Tokens
# =========================================================================


@pytest.fixture(scope="function")
def admin_token(app, admin_user):
    """
    Create a valid JWT access token for admin user.
    Scope: function (Fresh token for each test).
    """
    with app.app_context():
        token = create_access_token(
            identity=str(admin_user.id),
            additional_claims={'role': admin_user.role, 'username': admin_user.username}
        )
    return token


@pytest.fixture(scope="function")
def analyst_token(app, analyst_user):
    """
    Create a valid JWT access token for analyst user.
    Scope: function (Fresh token for each test).
    """
    with app.app_context():
        token = create_access_token(
            identity=str(analyst_user.id),
            additional_claims={'role': analyst_user.role, 'username': analyst_user.username}
        )
    return token


@pytest.fixture(scope="function")
def viewer_token(app, viewer_user):
    """
    Create a valid JWT access token for viewer user.
    Scope: function (Fresh token for each test).
    """
    with app.app_context():
        token = create_access_token(
            identity=str(viewer_user.id),
            additional_claims={'role': viewer_user.role, 'username': viewer_user.username}
        )
    return token


@pytest.fixture(scope="function")
def admin_refresh_token(app, admin_user):
    """
    Create a valid JWT refresh token for admin user.
    Scope: function (Fresh token for each test).
    """
    with app.app_context():
        token = create_refresh_token(identity=str(admin_user.id))
    return token


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    """
    Create Authorization headers with admin token.
    Scope: function.
    """
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def analyst_headers(analyst_token):
    """
    Create Authorization headers with analyst token.
    Scope: function.
    """
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture(scope="function")
def viewer_headers(viewer_token):
    """
    Create Authorization headers with viewer token.
    Scope: function.
    """
    return {"Authorization": f"Bearer {viewer_token}"}

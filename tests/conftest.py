import pytest

# Assuming 'app' imports create_app and 'app.extensions' imports the db instance
from app import create_app
from app.extensions import db as _db

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


@pytest.fixture(scope="session")
def db(app):
    """
    Initializes and cleans up the database tables for the session.
    Scope: session (Tables are created before the first test and dropped after the last).
    """
    # Create all tables defined in the models
    _db.create_all()

    yield _db

    # Drop all tables after the test session is complete
    _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    A test client for making requests to the application.
    Scope: function (A fresh client is provided for every test function).
    """
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def session_cleanup(db):
    """
    Automatically runs before and after every test function to ensure a clean session.
    This is necessary to clear any data that might have been committed in a test.
    """
    # The yield pauses the fixture until the test finishes
    yield

    # Teardown: Remove the session and clean up
    db.session.remove()
    # Note: Since the DB is in-memory and created/dropped per session, this is usually fast enough.

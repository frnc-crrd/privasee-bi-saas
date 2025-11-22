# app/__init__.py
import os
from typing import Any, Optional

from dotenv import load_dotenv
from flask import Flask

# Import extensions and models to ensure they are registered
from app.extensions import bcrypt, db, login_manager
from app.models import User


def create_app(config_overrides: Optional[dict[str, Any]] = None) -> Flask:
    """
    Application Factory Pattern
    ----------------------------
    Constructs and configures the Flask application instance.
    Supports configuration overrides for testing environments.

    Args:
        config_overrides: Dictionary of configuration settings
            to override default environment configuration. Primarily used for
            testing with in-memory databases or modified settings.

    Returns:
        Fully initialized and configured application instance.

    Raises:
        RuntimeError: If critical configuration values (SECRET_KEY, AUTH_DB_URI)
            are missing from environment variables.
    """
    # Load environment variables from .env file (ignored if already loaded)
    load_dotenv()

    # Initialize Flask application instance
    app = Flask(__name__)

    # =========================================================================
    # Configuration Layer
    # =========================================================================
    # Security: Session signing key (required for Flask-Login and CSRF)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Database: PostgreSQL connection string for authentication database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("AUTH_DB_URI")

    # Performance: Disable modification tracking to reduce memory overhead
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Apply configuration overrides (used primarily in testing environments)
    if config_overrides:
        app.config.update(config_overrides)  # type: ignore[arg-type]

    # Validation: Ensure critical configuration values are present
    # Only validate if not in testing mode (testing provides its own config)
    if not app.config.get("TESTING", False):  # type: ignore[arg-type]
        if not app.config["SECRET_KEY"] or not app.config["SQLALCHEMY_DATABASE_URI"]:
            raise RuntimeError(
                "Critical configuration missing: SECRET_KEY or AUTH_DB_URI "
                "not found in environment variables"
            )

    # =========================================================================
    # Extension Initialization
    # =========================================================================
    # Initialize SQLAlchemy ORM for database operations
    db.init_app(app)  # type: ignore[arg-type]

    # Initialize Bcrypt for secure password hashing
    bcrypt.init_app(app)  # type: ignore[arg-type]

    # Initialize Flask-Login for session-based authentication
    login_manager.init_app(app)  # type: ignore[arg-type]

    # =========================================================================
    # Flask-Login User Loader Callback
    # =========================================================================
    # This callback reloads the User object from the user ID stored in session
    # Note: Function is registered as callback by decorator, not directly called
    @login_manager.user_loader  # type: ignore[misc]
    def load_user(user_id: str) -> Optional[User]:  # pyright: ignore[reportUnusedFunction]
        """
        Reload user object from the user ID stored in the session.

        Args:
            user_id: User identifier stored in the session cookie.

        Returns:
            User object if found, None otherwise.
        """
        return db.session.get(User, int(user_id))

    # =========================================================================
    # Database Initialization
    # =========================================================================
    # Ensure database tables exist on application startup
    with app.app_context():
        # Create all tables defined in models (development/testing only)
        # Production environments should use Alembic migrations instead
        db.create_all()

        # Log successful initialization (suppress in testing to reduce noise)
        if not app.config.get("TESTING", False):  # type: ignore[arg-type]
            print(">> System: Database tables verified/created successfully.")

    # =========================================================================
    # Blueprint Registration
    # =========================================================================
    # Register application blueprints for modular route organization
    # TODO: Uncomment when blueprints are implemented
    # from app.routes.auth_routes import auth_bp
    # app.register_blueprint(auth_bp, url_prefix='/auth')

    # from app.routes.api_routes import api_bp
    # app.register_blueprint(api_bp, url_prefix='/api')

    return app

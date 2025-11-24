# app/__init__.py
from typing import Any, Optional

from flask import Flask

# Import core configuration and extensions
from app.core.config import Settings, get_settings
from app.extensions import bcrypt, db, login_manager
from app.models import User


def create_app(config_overrides: Optional[dict[str, Any]] = None) -> Flask:
    """
    Application Factory Pattern
    ----------------------------
    Constructs and configures the Flask application instance.
    Supports configuration overrides for testing environments.

    Uses Pydantic Settings for type-safe, validated configuration management.
    All configuration values are loaded from environment variables with
    comprehensive validation and defaults.

    Args:
        config_overrides: Dictionary of configuration settings
            to override default environment configuration. Primarily used for
            testing with in-memory databases or modified settings.

    Returns:
        Fully initialized and configured application instance.

    Raises:
        ValidationError: If configuration validation fails (Pydantic)
        RuntimeError: If critical configuration values are invalid
    """
    # Initialize Flask application instance
    app = Flask(__name__)

    # =========================================================================
    # Configuration Layer (Pydantic Settings)
    # =========================================================================
    # Load validated settings from environment variables
    # This will raise ValidationError if any required field is missing
    # or if validation rules are violated
    settings: Settings = get_settings()

    # Apply settings to Flask configuration
    # Security: Session signing key (validated by Pydantic)
    app.config["SECRET_KEY"] = settings.SECRET_KEY

    # Database: PostgreSQL connection string for authentication database
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.get_sqlalchemy_database_uri()

    # SQLAlchemy: Performance and connection pool settings
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SQLALCHEMY_ECHO"] = settings.SQLALCHEMY_ECHO
    app.config["SQLALCHEMY_POOL_SIZE"] = settings.SQLALCHEMY_POOL_SIZE
    app.config["SQLALCHEMY_MAX_OVERFLOW"] = settings.SQLALCHEMY_MAX_OVERFLOW
    app.config["SQLALCHEMY_POOL_TIMEOUT"] = settings.SQLALCHEMY_POOL_TIMEOUT

    # Application: Environment flags
    app.config["DEBUG"] = settings.DEBUG
    app.config["TESTING"] = settings.TESTING
    app.config["ENVIRONMENT"] = settings.ENVIRONMENT

    # Apply configuration overrides (used primarily in testing environments)
    if config_overrides:
        app.config.update(config_overrides)  # type: ignore[arg-type]
        # If TESTING flag is set in overrides, mark as testing environment
        if config_overrides.get("TESTING"):
            settings.TESTING = True

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
        if not settings.is_testing():
            print(
                f">> System: Database tables verified/created successfully. "
                f"Environment: {settings.ENVIRONMENT}"
            )

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

# app/__init__.py
from datetime import timedelta
from typing import Any, Optional

from flask import Flask

# Import core configuration and extensions
from app.core.config import Settings, get_settings
from app.extensions import bcrypt, db, login_manager, jwt, cache, limiter
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

    # Security: Session cookie configuration
    # Only enforce HTTPS cookies in production (allows local development over HTTP)
    app.config["SESSION_COOKIE_SECURE"] = settings.SESSION_COOKIE_SECURE and settings.is_production()
    app.config["SESSION_COOKIE_HTTPONLY"] = settings.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = settings.SESSION_COOKIE_SAMESITE
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=settings.PERMANENT_SESSION_LIFETIME)

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
    # JWT and Caching Configuration
    # =========================================================================
    # Configure JWT settings
    app.config["JWT_SECRET_KEY"] = settings.SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800  # 7 days
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"

    # Initialize JWT manager
    jwt.init_app(app)  # type: ignore[arg-type]

    # Configure caching (simple in-memory for development)
    app.config["CACHE_TYPE"] = "simple"  # Change to "redis" in production
    app.config["CACHE_DEFAULT_TIMEOUT"] = 300

    # Initialize cache
    cache.init_app(app)  # type: ignore[arg-type]

    # =========================================================================
    # Rate Limiting Configuration
    # =========================================================================
    # Configure rate limiting storage (Redis in production, memory in dev/test)
    rate_limit_storage = "memory://"
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL and not settings.is_testing():
        rate_limit_storage = settings.REDIS_URL.replace('/0', '/2')  # Use Redis DB 2 for rate limiting

    app.config["RATELIMIT_STORAGE_URL"] = rate_limit_storage
    limiter.init_app(app)  # type: ignore[arg-type]

    if not settings.is_testing():
        app.logger.info(f"Rate limiting initialized with storage: {rate_limit_storage}")

    # =========================================================================
    # CORS Configuration
    # =========================================================================
    # Initialize CORS for cross-origin requests from frontend
    from flask_cors import CORS

    cors_origins = settings.CORS_ORIGINS.split(',')
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": settings.CORS_METHODS.split(','),
            "allow_headers": settings.CORS_ALLOW_HEADERS.split(','),
            "expose_headers": ["X-Request-ID", "X-Total-Count"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })

    if not settings.is_testing():
        app.logger.info(f"CORS initialized with origins: {cors_origins}")

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
    # Exception Handlers Registration
    # =========================================================================
    # Register global exception handlers for API error responses
    from app.exceptions.handlers import register_error_handlers
    register_error_handlers(app)

    # =========================================================================
    # Security Middleware Registration
    # =========================================================================
    # Apply security headers to all responses
    from app.middleware.security_middleware import (
        apply_security_headers,
        track_request_context,
        log_request_info,
        log_response_info
    )

    @app.before_request
    def before_request_handler():
        """Track request context and log incoming requests."""
        track_request_context()
        if not settings.is_testing():
            log_request_info()

    @app.after_request
    def after_request_handler(response):
        """Apply security headers and log response info."""
        response = apply_security_headers(response)
        if not settings.is_testing():
            response = log_response_info(response)
        return response

    # =========================================================================
    # Metrics Middleware Registration
    # =========================================================================
    # Initialize Prometheus metrics collection
    try:
        from app.core.metrics import MetricsMiddleware
        metrics_middleware = MetricsMiddleware(app)
        if not settings.is_testing():
            app.logger.info("Metrics collection initialized at /metrics")
    except ImportError:
        # Metrics are optional, log warning but don't fail
        if not settings.is_testing():
            app.logger.warning("Prometheus metrics not available (prometheus-client not installed)")

    # =========================================================================
    # Blueprint Registration
    # =========================================================================
    # Register application blueprints for modular route organization
    from app.routes import register_blueprints
    register_blueprints(app)

    # Register health check routes
    from app.routes.health_routes import health_bp
    app.register_blueprint(health_bp)
    if not settings.is_testing():
        app.logger.info("Health check endpoints registered at /health/*")

    # =========================================================================
    # Dashboard Integration
    # =========================================================================
    # Integrate Dash dashboards with Flask app
    # Dashboards are mounted at /dashboard/ and share authentication
    try:
        from app.dashboard import create_dash_app
        dash_app = create_dash_app(app, url_base_pathname='/dashboard/')
        if not settings.is_testing():
            app.logger.info("Dashboard integrated successfully at /dashboard/")
    except Exception as e:
        # Dashboard is optional, log error but don't fail app creation
        if not settings.is_testing():
            app.logger.warning(f"Dashboard integration failed: {str(e)}")

    # Log successful application creation
    if not settings.is_testing():
        app.logger.info(f"Application created successfully. Environment: {settings.ENVIRONMENT}")

    return app

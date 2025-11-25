# app/extensions.py
"""
Extensions Module
-----------------
Initializes Flask extensions separately to avoid circular imports.
This follows the 'Application Factory' pattern.
"""

from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_caching import Cache

# Initialize SQLAlchemy with declarative base connection
# This object will be used by models.py to define tables
db = SQLAlchemy()

# Initialize Bcrypt for secure password hashing
bcrypt = Bcrypt()

# Initialize Flask-Login for session management
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # Redirect here if user is not logged in
login_manager.login_message_category = "info"

# Initialize Flask-JWT-Extended for token-based authentication
# Handles JWT creation, validation, and refresh tokens
jwt = JWTManager()

# Initialize Flask-Caching for response and query caching
# Supports multiple backends (simple, redis, memcached)
cache = Cache()

# Initialize Flask-Limiter for rate limiting
# Protects against brute force and API abuse
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day", "50/hour"],
    storage_uri="memory://",  # Will be overridden in app factory with Redis
    strategy="fixed-window"
)

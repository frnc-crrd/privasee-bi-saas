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

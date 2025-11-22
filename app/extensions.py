# app/extensions.py
"""
Extensions Module
-----------------
Initializes Flask extensions separately to avoid circular imports.
This follows the 'Application Factory' pattern.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# Initialize SQLAlchemy with declarative base connection
# This object will be used by models.py to define tables
db = SQLAlchemy()

# Initialize Bcrypt for secure password hashing
bcrypt = Bcrypt()

# Initialize Flask-Login for session management
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Redirect here if user is not logged in
login_manager.login_message_category = 'info'

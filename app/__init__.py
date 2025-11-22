# app/__init__.py
import os
from flask import Flask
from dotenv import load_dotenv

# Import extensions and models to ensure they are registered
from app.extensions import db, bcrypt, login_manager
from app.models import User

def create_app():
    """
    Application Factory
    -------------------
    Constructs the Flask application instance, configures it from environment variables,
    and initializes all extensions.
    
    Returns:
        Flask: The initialized application instance ready to run.
    """
    # 1. Load environment variables from .env file
    load_dotenv()

    # 2. Initialize Flask
    app = Flask(__name__)

    # 3. Configuration Layer
    # Security: Used for signing session cookies (Crucial for Flask-Login)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    
    # Database: Connection string to PostgreSQL Auth DB
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('AUTH_DB_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable overhead

    # Validation: Ensure critical configs are present
    if not app.config['SECRET_KEY'] or not app.config['SQLALCHEMY_DATABASE_URI']:
        raise RuntimeError("Critical configuration missing: SECRET_KEY or AUTH_DB_URI not found in .env")

    # 4. Initialize Extensions with the App Context
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # 5. Flask-Login User Loader
    # This callback is used to reload the user object from the user ID stored in the session.
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 6. Context Initialization
    # This block runs only once when the app starts.
    # It ensures the database tables exist in PostgreSQL.
    with app.app_context():
        # In Production, use Alembic Migrations instead of create_all()
        db.create_all()
        print(">> System: Database tables verified/created successfully.")

    # 7. Register Blueprints (Routes)
    # We will register auth_routes and api_routes here in the next steps.
    # from app.routes.auth_routes import auth_bp
    # app.register_blueprint(auth_bp)

    return app

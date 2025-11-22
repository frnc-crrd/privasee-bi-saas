# run.py
"""
Entry Point
-----------
This script initializes the Application Factory and runs the server.
Intended for development use. For production, use Gunicorn to serve 'app'.
"""

from app import create_app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    # Run the server in debug mode for development
    # Host '0.0.0.0' makes the server accessible within the local network/containers
    print(">> Starting Privasee BI SaaS Server...")
    app.run(host='0.0.0.0', port=5000, debug=True)

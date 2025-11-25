#!/bin/bash
set -e

# Privasee BI SaaS Docker Entrypoint Script
# This script performs initialization tasks before starting the application

echo "========================================="
echo "Privasee BI SaaS Starting..."
echo "========================================="

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."

    until python -c "
import psycopg2
import os
import sys
try:
    # Extract connection details from AUTH_DB_URI
    db_uri = os.getenv('AUTH_DB_URI', '')
    if not db_uri:
        print('AUTH_DB_URI not set')
        sys.exit(1)

    # Simple connection test
    import urllib.parse as urlparse
    url = urlparse.urlparse(db_uri)
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.path[1:],
        connect_timeout=5
    )
    conn.close()
    print('PostgreSQL is ready!')
    sys.exit(0)
except Exception as e:
    print(f'PostgreSQL not ready: {e}')
    sys.exit(1)
" 2>&1; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done

    echo "PostgreSQL is up!"
}

# Function to wait for Redis to be ready
wait_for_redis() {
    echo "Waiting for Redis to be ready..."

    REDIS_URL=${REDIS_URL:-""}

    if [ -z "$REDIS_URL" ]; then
        echo "REDIS_URL not set, skipping Redis check"
        return 0
    fi

    until python -c "
import redis
import os
import sys
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    r = redis.from_url(redis_url, socket_connect_timeout=5)
    r.ping()
    print('Redis is ready!')
    sys.exit(0)
except Exception as e:
    print(f'Redis not ready: {e}')
    sys.exit(1)
" 2>&1; do
        echo "Redis is unavailable - sleeping"
        sleep 2
    done

    echo "Redis is up!"
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."

    if [ -d "alembic" ]; then
        echo "Alembic directory found, running migrations..."
        alembic upgrade head
        echo "Migrations completed!"
    else
        echo "No Alembic directory found, skipping migrations"
        echo "WARNING: Using db.create_all() - not recommended for production!"
    fi
}

# Function to create initial admin user
create_admin_user() {
    echo "Checking for admin user..."

    python -c "
from app import create_app
from app.models import User
from app.extensions import db

app = create_app()
with app.app_context():
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        print('Creating default admin user...')
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        admin.set_password('Admin123!')  # Change this in production!
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: admin@example.com / Admin123!')
        print('IMPORTANT: Change the default password immediately!')
    else:
        print('Admin user already exists')
" 2>&1
}

# Function to display environment info
display_environment_info() {
    echo "========================================="
    echo "Environment Information:"
    echo "========================================="
    echo "Python Version: $(python --version)"
    echo "Flask Environment: ${FLASK_ENV:-not set}"
    echo "Workers: ${WORKERS:-auto}"
    echo "Port: ${PORT:-5000}"
    echo "Log Level: ${LOG_LEVEL:-info}"
    echo "========================================="
}

# Main execution flow
main() {
    display_environment_info

    # Wait for dependencies
    wait_for_postgres
    wait_for_redis

    # Run migrations
    run_migrations

    # Create admin user (only if CREATE_ADMIN=true)
    if [ "${CREATE_ADMIN}" = "true" ]; then
        create_admin_user
    fi

    echo "========================================="
    echo "Starting application..."
    echo "========================================="

    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"

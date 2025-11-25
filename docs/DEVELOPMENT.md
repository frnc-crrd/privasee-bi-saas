# Development Guide

Local development setup and workflows for Privasee BI SaaS.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Database Migrations](#database-migrations)
- [Code Quality](#code-quality)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)

## Prerequisites

### Required Software

- Python 3.11+
- PostgreSQL 14+
- Docker and Docker Compose
- Git
- VS Code or PyCharm (recommended)

### Recommended Tools

- pyenv (Python version management)
- poetry (alternative to pip)
- pgAdmin or DBeaver (database GUI)
- Redis Desktop Manager

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/privasee-bi-saas.git
cd privasee-bi-saas
```

### 2. Create Virtual Environment

Using venv:

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Using pyenv:

```bash
pyenv install 3.11.0
pyenv virtualenv 3.11.0 privasee
pyenv activate privasee
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov ruff pyright bandit safety
```

### 4. Start Database Services

```bash
# Start PostgreSQL and Redis containers
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with local values
```

Example `.env` for development:

```bash
# Flask
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# Database
AUTH_DB_URI=postgresql://auth_admin:SecretAuthPassword!@localhost:5432/privasee_users
DESTINATION__DUCKDB__CREDENTIALS=duckdb:///data/analytical_cube.duckdb

# JWT
JWT_SECRET_KEY=dev-jwt-secret-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TYPE=simple

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# ETL (configure with your SQL Server)
SOURCES__SQL_SERVER__CREDENTIALS=<your-sql-server-connection-string>
```

### 6. Initialize Database

```bash
# Run migrations (when Alembic is configured)
alembic upgrade head

# Or use Flask-Migrate
flask db upgrade
```

### 7. Create Test Data

```bash
# Start Flask shell
flask shell

# Create admin user
>>> from app.models import User
>>> from app.extensions import db
>>> admin = User(username='admin', email='admin@example.com', role='admin')
>>> admin.set_password('Admin123!')
>>> db.session.add(admin)
>>> db.session.commit()

# Create test user
>>> user = User(username='testuser', email='test@example.com', role='viewer')
>>> user.set_password('Test123!')
>>> db.session.add(user)
>>> db.session.commit()
>>> exit()
```

### 8. Run ETL Pipeline

```bash
# Ingest sample data
python pipelines/ingest_sales_data.py
```

### 9. Start Development Server

```bash
# Start Flask development server
python run.py

# Application runs at http://localhost:5000
# Dashboard at http://localhost:5000/dashboard/
```

## Development Workflow

### Branch Strategy

```bash
# Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feat/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push to remote
git push origin feat/your-feature-name

# Create pull request to develop
```

### Commit Message Format

Follow conventional commits:

```
feat: add user authentication
fix: resolve database connection issue
docs: update API documentation
test: add unit tests for user service
refactor: improve query performance
chore: update dependencies
```

### Code Style

Follow PEP 8 and project conventions:

- Use double quotes for strings
- Maximum line length: 100 characters
- Use type hints for all function signatures
- Write docstrings in Google style
- No emojis in code or comments

## Testing

### Run All Tests

```bash
# Run full test suite
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth_service.py

# Run tests matching pattern
pytest -k "test_login"

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Run Quality Gate

```bash
# Run automated quality checks (Ruff + Pytest)
./run_checks.sh
```

This script:
1. Runs Ruff linter with auto-fix
2. Runs Ruff formatter
3. Runs full test suite

Exit code 0 means ready to commit.

### Test Coverage Requirements

- Overall coverage: >85%
- Critical paths: 100%
- New code: >90%

### Writing Tests

Example unit test:

```python
def test_user_login(client, db):
    """Test user login with valid credentials."""
    # Create user
    user = User(username="test", email="test@example.com")
    user.set_password("Test123!")
    db.session.add(user)
    db.session.commit()

    # Login request
    response = client.post('/api/v1/auth/login', json={
        'email': 'test@example.com',
        'password': 'Test123!'
    })

    # Assertions
    assert response.status_code == 200
    assert 'access_token' in response.json['data']
```

## Database Migrations

### Using Alembic

```bash
# Create new migration
alembic revision --autogenerate -m "add user table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Using Flask-Migrate

```bash
# Initialize migrations (first time only)
flask db init

# Create migration
flask db migrate -m "add user table"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## Code Quality

### Linting

```bash
# Check code style
ruff check .

# Auto-fix issues
ruff check . --fix

# Check specific file
ruff check app/services/auth_service.py
```

### Formatting

```bash
# Format code
ruff format .

# Check formatting without changes
ruff format --check .
```

### Type Checking

```bash
# Run type checker
pyright

# Check specific file
pyright app/services/auth_service.py
```

### Security Scanning

```bash
# Scan for security issues
bandit -r app/

# Check dependency vulnerabilities
safety check
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Debugging

### Flask Debug Mode

Development server runs with debug mode enabled by default:

```python
# In run.py
app.run(debug=True, host='0.0.0.0', port=5000)
```

### VS Code Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "app",
        "FLASK_ENV": "development"
      },
      "args": [
        "run",
        "--no-debugger",
        "--no-reload"
      ],
      "jinja": true
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v"
      ]
    }
  ]
}
```

### PyCharm Debug Configuration

1. Run > Edit Configurations
2. Add > Python
3. Script path: `run.py`
4. Working directory: project root
5. Environment variables: Load from `.env`

### Database Debugging

Enable SQL query logging:

```python
# In config.py
SQLALCHEMY_ECHO = True
```

View queries in console output.

### Flask Shell

```bash
# Start interactive shell
flask shell

# Import models
>>> from app.models import User
>>> from app.extensions import db

# Query database
>>> User.query.all()
>>> User.query.filter_by(email='admin@example.com').first()

# Test functions
>>> from app.services.auth_service import AuthService
>>> service = AuthService()
>>> user = service.authenticate_user('admin@example.com', 'Admin123!')
>>> print(user.username)
```

## Common Tasks

### Add New API Endpoint

1. Create route handler in `app/routes/v1/`:

```python
@bp.route('/endpoint', methods=['POST'])
@jwt_required_custom()
def new_endpoint():
    return success_response(data={}, message="Success")
```

2. Add service method in `app/services/`:

```python
def new_service_method(self, data: dict) -> dict:
    # Business logic
    return result
```

3. Add repository method in `app/repositories/` if needed
4. Write tests in `tests/`
5. Update API documentation in `docs/API.md`

### Add New Model

1. Define model in `app/models.py`:

```python
class NewModel(db.Model):
    __tablename__ = 'new_table'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
```

2. Create migration:

```bash
alembic revision --autogenerate -m "add new_table"
alembic upgrade head
```

3. Add repository in `app/repositories/`
4. Write tests

### Add ETL Pipeline

1. Create pipeline in `pipelines/`:

```python
# pipelines/ingest_new_data.py
import dlt

@dlt.source
def new_data_source():
    # Extract logic
    pass

if __name__ == '__main__':
    pipeline = dlt.pipeline(
        pipeline_name='new_data',
        destination='duckdb',
        dataset_name='new_dataset'
    )
    pipeline.run(new_data_source())
```

2. Configure connection in `.env`
3. Test pipeline
4. Schedule with cron or Airflow

### Add Dashboard Component

1. Create chart in `app/dashboard/components/charts.py`
2. Add to layout in `app/dashboard/layouts/`
3. Register callback in `app/dashboard/callbacks/`
4. Test interactivity

### Update Dependencies

```bash
# Update requirements.txt
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt

# Or use pip-tools
pip-compile requirements.in
pip-sync
```

### Run Production Server Locally

```bash
# Install Gunicorn
pip install gunicorn gevent

# Run with Gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 --worker-class gevent --timeout 120 run:app
```

## Database Access

### PostgreSQL CLI

```bash
# Connect to database
docker-compose exec auth_db psql -U auth_admin -d privasee_users

# Common commands
\dt              # List tables
\d users         # Describe users table
\l               # List databases
\q               # Quit
```

### Adminer Web UI

```
URL: http://localhost:8080
System: PostgreSQL
Server: auth_db
Username: auth_admin
Password: SecretAuthPassword!
Database: privasee_users
```

### DuckDB CLI

```bash
# Install DuckDB CLI
pip install duckdb

# Connect to analytical cube
duckdb data/analytical_cube.duckdb

# Query data
SELECT * FROM sales_mart.Productos LIMIT 10;
.tables          # List tables
.schema          # Show schema
.quit            # Exit
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| FLASK_ENV | Environment mode | development |
| FLASK_DEBUG | Debug mode | True |
| SECRET_KEY | Flask secret key | - |
| AUTH_DB_URI | PostgreSQL connection string | - |
| JWT_SECRET_KEY | JWT signing key | - |
| JWT_ACCESS_TOKEN_EXPIRES | Access token lifetime (seconds) | 3600 |
| JWT_REFRESH_TOKEN_EXPIRES | Refresh token lifetime (seconds) | 604800 |
| REDIS_URL | Redis connection string | - |
| CACHE_TYPE | Cache backend | simple |
| LOG_LEVEL | Logging level | DEBUG |
| LOG_FORMAT | Log format (text/json) | text |
| SOURCES__SQL_SERVER__CREDENTIALS | SQL Server connection | - |

## Troubleshooting

### Import Errors

```bash
# Verify virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Connection Errors

```bash
# Check containers are running
docker-compose ps

# Restart containers
docker-compose restart auth_db

# Check connection string
echo $AUTH_DB_URI
```

### Port Already in Use

```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Migration Conflicts

```bash
# Reset migrations (development only!)
alembic downgrade base
alembic upgrade head
```

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Dash Documentation](https://dash.plotly.com/)

## Getting Help

- Check `CLAUDE.md` for project conventions
- Review existing code for patterns
- Ask questions in team chat
- Create issue in GitHub for bugs

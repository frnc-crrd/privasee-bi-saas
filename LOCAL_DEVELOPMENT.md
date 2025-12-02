# Local Development Guide

Complete guide for running Privasee BI SaaS on your local machine for development and testing.

## Overview

This guide focuses on getting you up and running quickly to:
1. View interactive **Dash/Plotly dashboards** with real data
2. Explore **REST API endpoints** via Swagger UI
3. Test the full application locally without Docker

## Prerequisites

### Required Software

```bash
# Python 3.11 or higher
python3 --version

# PostgreSQL 14+ (for authentication database)
psql --version

# Git
git --version
```

### Installation Steps

#### 1. Install PostgreSQL (if not already installed)

**Fedora/RHEL:**
```bash
sudo dnf install postgresql postgresql-server
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

#### 2. Create PostgreSQL Database

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create database and user
CREATE DATABASE privasee_users;
CREATE USER auth_admin WITH ENCRYPTED PASSWORD 'SecretAuthPassword!';
GRANT ALL PRIVILEGES ON DATABASE privasee_users TO auth_admin;

# Exit psql
\q
```

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository (if not already cloned)
git clone <repository-url>
cd privasee-bi-saas

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

The `.env` file is already configured for local development. Verify these key settings:

```bash
# View current configuration
cat .env
```

Key variables (already set):
- `ENVIRONMENT=development` - Enables debug mode and Swagger UI
- `DEBUG=true` - Flask debug mode for auto-reload
- `AUTH_DB_URI` - PostgreSQL connection (localhost:5432)
- `DESTINATION__DUCKDB__CREDENTIALS` - DuckDB path for analytics
- `RATE_LIMIT_ENABLED=false` - Disabled for local dev

### 3. Generate Sample Data

Create synthetic sales data for dashboards (5000 transactions, 50 products, 10 locations):

```bash
python scripts/seed_duckdb.py
```

Expected output:
```
==============================================================
DuckDB Sample Data Generator
==============================================================
>> Target database: /path/to/data/analytical_cube.duckdb
>> Generating sample data...
>> Generated 10 branches
>> Generated 5 product categories
>> Generated 15 subcategories
>> Generated 50 products
>> Generated 5000 sales transactions
...
✓ Sample data seeded successfully!
```

This creates:
- `data/analytical_cube.duckdb` - DuckDB analytical database
- Tables: Sucursal, Linea, Sub_Linea, Productos, Ventas

### 4. Start the Application

```bash
python run.py
```

Expected output:
```
>> System: Database tables auto-created (development mode). Environment: development
INFO:app.core.logging_config:Health check endpoints registered at /health/*
INFO:app.core.logging_config:Dashboard integrated successfully at /dashboard/
INFO:app.core.logging_config:Swagger UI initialized successfully at /apidocs/
INFO:app.core.logging_config:Application created successfully. Environment: development
>> Starting Privasee BI SaaS Server...
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5000
```

## Access Points

Once the server is running, access these URLs:

### 1. Swagger UI - API Documentation
**URL:** http://localhost:5000/apidocs/

**Features:**
- Interactive API documentation
- Test endpoints directly from browser
- View request/response schemas
- JWT authentication support

**Available Endpoints:**
- **Authentication:** `/api/v1/auth/*` (register, login, logout)
- **Users:** `/api/v1/users/*` (CRUD operations)
- **Analytics:** `/api/v1/analytics/*` (sales metrics, trends)
- **Health:** `/health/*` (system health checks)

**Quick Test:**
1. Open http://localhost:5000/apidocs/
2. Navigate to "Authentication" section
3. Try `POST /api/v1/auth/register` to create a test user
4. Use returned `access_token` for authenticated requests

### 2. Dash Dashboard - Interactive BI
**URL:** http://localhost:5000/dashboard/

**Features:**
- Sales summary KPI cards
- Interactive time-series charts
- Product performance charts
- Location breakdown
- Date range filters
- Category filters

**Dashboard Components:**
- Total Sales Revenue
- Total Orders
- Average Order Value
- Growth Rate
- Sales Trends (line chart)
- Top Products (bar chart)
- Sales by Location (table)

### 3. Health Checks
**URLs:**
- http://localhost:5000/health - Overall health
- http://localhost:5000/health/liveness - Service alive
- http://localhost:5000/health/readiness - Ready for traffic

### 4. Prometheus Metrics
**URL:** http://localhost:5000/metrics

Metrics available:
- Request latency (p50, p95, p99)
- HTTP status codes
- Database query performance
- Cache hit rates

## Testing the API with Swagger UI

### Step 1: Register a User

1. Open http://localhost:5000/apidocs/
2. Find `POST /api/v1/auth/register` endpoint
3. Click "Try it out"
4. Enter request body:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPass123!",
  "role": "analyst"
}
```
5. Click "Execute"
6. Copy the `access_token` from response

### Step 2: Use JWT Token

1. Click the "Authorize" button at the top of Swagger UI
2. Enter: `Bearer <your_access_token>`
3. Click "Authorize"
4. Now all endpoints will include authentication

### Step 3: Test Analytics Endpoint

1. Find `GET /api/v1/analytics/sales/summary`
2. Click "Try it out"
3. Optionally add date filters:
   - start_date: `2024-01-01`
   - end_date: `2024-12-31`
4. Click "Execute"
5. View sales metrics in response

## Viewing the Dashboard

### Step 1: Access Dashboard

1. Open http://localhost:5000/dashboard/
2. View the Sales Analytics Dashboard

### Step 2: Interact with Filters

**Date Range Filter:**
- Select start date (e.g., last 30 days)
- Select end date (today)
- Charts update automatically

**Category Filter:**
- Select product category (Electrónica, Ropa, etc.)
- View filtered results

### Step 3: Explore Charts

**KPI Cards (Top Row):**
- Total Sales: Aggregate revenue
- Total Orders: Number of transactions
- Avg Order Value: Revenue per order
- Growth Rate: YoY percentage change

**Sales Trend Chart:**
- Daily/weekly sales over time
- Hover for detailed values
- Interactive zoom/pan

**Product Performance Chart:**
- Top 10 products by revenue
- Horizontal bar chart
- Click to filter

## Development Workflow

### Making Changes

1. **Backend Changes** (Flask routes, services):
   - Edit files in `app/` directory
   - Flask auto-reloads on save (DEBUG=true)
   - Check terminal for errors

2. **Dashboard Changes** (Dash components):
   - Edit files in `app/dashboard/` directory
   - Refresh browser to see changes
   - Check browser console for errors

3. **Database Changes** (add tables/fields):
   - Edit models in `app/models.py`
   - Create migration: `flask db migrate -m "description"`
   - Apply migration: `flask db upgrade`

### Useful Commands

```bash
# Run tests
pytest -v

# Run tests with coverage
pytest --cov=app --cov-report=html

# Format code
ruff format .

# Lint code
ruff check . --fix

# Type check
pyright

# Run all quality checks
./run_checks.sh

# Create database migration
flask db migrate -m "Add new field"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade

# Reset DuckDB data
rm data/analytical_cube.duckdb
python scripts/seed_duckdb.py
```

## Troubleshooting

### Issue: PostgreSQL Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Verify connection
psql -U auth_admin -d privasee_users -h localhost
```

### Issue: DuckDB File Not Found

```
FileNotFoundError: analytical_cube.duckdb
```

**Solution:**
```bash
# Generate sample data
python scripts/seed_duckdb.py
```

### Issue: Import Error (Missing Dependencies)

```
ModuleNotFoundError: No module named 'flasgger'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Rate Limit Errors

```
429 Too Many Requests
```

**Solution:**
```bash
# Verify rate limiting is disabled in .env
grep RATE_LIMIT_ENABLED .env
# Should show: RATE_LIMIT_ENABLED=false

# Restart server
python run.py
```

### Issue: Swagger UI Not Loading

```
404 Not Found at /apidocs/
```

**Solution:**
- Swagger UI only loads in development/staging
- Verify `.env` has `ENVIRONMENT=development`
- Check logs for Swagger initialization errors
- Ensure `flasgger` is installed

### Issue: Dashboard Shows No Data

**Solution:**
```bash
# Verify DuckDB has data
python -c "import duckdb; conn = duckdb.connect('data/analytical_cube.duckdb'); print(conn.execute('SELECT COUNT(*) FROM sales_mart.Ventas').fetchone())"

# If returns (0,), regenerate data
python scripts/seed_duckdb.py
```

### Issue: JWT Token Expired

```
401 Unauthorized: Token has expired
```

**Solution:**
1. Register a new user or login again
2. Use the new `access_token`
3. Update authorization in Swagger UI

## Project Structure (Key Directories)

```
privasee-bi-saas/
├── app/
│   ├── routes/v1/          # API endpoints (auth, users, analytics)
│   ├── services/           # Business logic
│   ├── repositories/       # Database queries
│   ├── dashboard/          # Dash dashboards
│   │   ├── layouts/        # Dashboard layouts
│   │   ├── callbacks/      # Interactive callbacks
│   │   └── components/     # Reusable components
│   └── schemas/            # Pydantic validation schemas
├── scripts/
│   └── seed_duckdb.py      # Sample data generator
├── data/
│   └── analytical_cube.duckdb  # DuckDB database (git-ignored)
├── tests/                  # Unit and integration tests
├── .env                    # Environment configuration
├── run.py                  # Development server entry point
└── LOCAL_DEVELOPMENT.md    # This file
```

## Next Steps

### 1. Add Your Own Data

Replace sample data with real data from SQL Server:

```bash
# Configure SQL Server connection in .env
SOURCES__SQL_SERVER__CREDENTIALS="mssql+pyodbc://user:pass@host:port/db?driver=ODBC+Driver+18+for+SQL+Server"

# Run ETL pipeline
python pipelines/ingest_sales_data.py
```

### 2. Customize Dashboards

Edit dashboard files:
- `app/dashboard/layouts/sales_dashboard.py` - Layout
- `app/dashboard/callbacks/sales_callbacks.py` - Interactivity
- `app/dashboard/components/charts.py` - Chart components

### 3. Add API Endpoints

1. Create new route in `app/routes/v1/`
2. Add Swagger documentation (see examples in `auth_routes.py`)
3. Implement service logic in `app/services/`
4. Test in Swagger UI

### 4. Deploy to Production

When ready for production:
```bash
# Use production Docker Compose
docker compose -f docker-compose.prod.yml up -d --build

# Access at configured domain
# Swagger UI disabled in production (security)
```

## Additional Resources

- **CLAUDE.md** - Project architecture and standards
- **README.md** - Project overview
- **PHASE2_IMPLEMENTATION.md** - Roadmap
- **API Documentation** - http://localhost:5000/apidocs/
- **Dashboard** - http://localhost:5000/dashboard/

## Support

For issues or questions:
1. Check this guide first
2. Review error logs in terminal
3. Check PostgreSQL/DuckDB status
4. Verify environment configuration
5. Run health checks: http://localhost:5000/health

---

**Happy coding!**

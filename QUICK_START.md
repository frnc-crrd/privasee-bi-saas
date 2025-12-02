# Quick Start - Local Development

Ready-to-use local development environment for Privasee BI SaaS. This guide gets you up and running in less than 5 minutes.

## Prerequisites

You already have:
- Python 3.14 installed
- PostgreSQL running
- Virtual environment at `.venv/`
- All dependencies in `requirements.txt`

## One-Command Startup

```bash
./start_local.sh
```

This automated script will:
1. Activate virtual environment
2. Install/verify dependencies
3. Check PostgreSQL connection
4. Generate sample data (5000 sales transactions)
5. Start the Flask development server

## Manual Startup (3 Steps)

If you prefer manual control:

### Step 1: Install Swagger UI dependency
```bash
source .venv/bin/activate
pip install flasgger==0.9.7.1
```

### Step 2: Generate sample data
```bash
python scripts/seed_duckdb.py
```

Expected output:
```
======================================================================
Database Summary:
======================================================================
   Total Sales:        4,726
   Total Revenue:      $103,206,333.00
   Unique Products:    50
   Unique Branches:    10
======================================================================
✓ Sample data seeded successfully!
```

### Step 3: Start the server
```bash
python run.py
```

## Access Points

Once running, open these URLs:

### 1. Swagger UI - API Explorer
**http://localhost:5000/apidocs/**

Interactive API documentation where you can:
- Browse all endpoints
- Test requests directly
- View request/response schemas
- Use JWT authentication

**Quick Test Flow:**
1. Register user: `POST /api/v1/auth/register`
2. Copy `access_token` from response
3. Click "Authorize" button (top right)
4. Enter: `Bearer <your_token>`
5. Test analytics: `GET /api/v1/analytics/sales/summary`

### 2. Dash Dashboard - BI Visualizations
**http://localhost:5000/dashboard/**

Interactive sales analytics dashboard with:
- KPI cards (Total Sales, Orders, Avg Order Value, Growth)
- Sales trend charts (time series)
- Product performance charts
- Location breakdown
- Date range filters
- Category filters

**Features:**
- Real-time chart updates
- Interactive tooltips
- Zoom/pan capabilities
- Responsive design
- Powered by Plotly

### 3. Health Checks
- **http://localhost:5000/health** - Overall health
- **http://localhost:5000/health/liveness** - Service alive
- **http://localhost:5000/health/readiness** - Database ready

### 4. Prometheus Metrics
**http://localhost:5000/metrics**

Performance metrics:
- Request latency (p50, p95, p99)
- HTTP status codes
- Database query time
- Cache hit rates

## Sample API Workflow

### Example 1: Register and Login

```bash
# 1. Register a new user
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst1",
    "email": "analyst@example.com",
    "password": "SecurePass123!",
    "role": "analyst"
  }'

# Response includes access_token and refresh_token

# 2. Use token for authenticated requests
curl -X GET http://localhost:5000/api/v1/analytics/sales/summary \
  -H "Authorization: Bearer <your_access_token>"
```

### Example 2: Query Analytics

```bash
# Sales summary with date filter
curl -X GET "http://localhost:5000/api/v1/analytics/sales/summary?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <token>"

# Top products
curl -X GET "http://localhost:5000/api/v1/analytics/sales/products?limit=10" \
  -H "Authorization: Bearer <token>"

# Sales by location
curl -X GET http://localhost:5000/api/v1/analytics/sales/locations \
  -H "Authorization: Bearer <token>"
```

## Sample Data Overview

The seed script generates:

**Locations (10 branches):**
- Centro CDMX, Polanco, Santa Fe
- Monterrey, Guadalajara, Puebla
- Querétaro, Cancún, Tijuana, Mérida

**Product Categories (5):**
- Electrónica
- Ropa y Accesorios
- Hogar y Decoración
- Deportes
- Alimentos y Bebidas

**Products (50):** Mix of electronics, clothing, home goods, sports equipment, and food items

**Sales (5000 transactions):** Last 12 months with realistic patterns

## Swagger UI Screenshots Guide

### Authentication Section
1. Open http://localhost:5000/apidocs/
2. Look for **Authentication** tag (blue)
3. Endpoints available:
   - `POST /api/v1/auth/register`
   - `POST /api/v1/auth/login`
   - `POST /api/v1/auth/refresh`
   - `POST /api/v1/auth/logout`

### Analytics Section
1. Look for **Analytics** tag (blue)
2. Endpoints available:
   - `GET /api/v1/analytics/sales/summary`
   - `GET /api/v1/analytics/sales/products`
   - `GET /api/v1/analytics/sales/locations`
   - `GET /api/v1/analytics/sales/trends`

### Testing an Endpoint
1. Click on an endpoint to expand it
2. Click "Try it out" button
3. Fill in parameters (if any)
4. Click "Execute"
5. View response in "Responses" section below

### Using JWT Authentication
1. Register or login to get a token
2. Click "Authorize" button (top right, with lock icon)
3. Enter: `Bearer <your_access_token>`
4. Click "Authorize"
5. Click "Close"
6. Now all requests will include the token

## Dashboard Features

### KPI Cards (Top Row)
- **Total Sales:** Sum of all completed transactions
- **Total Orders:** Number of sales records
- **Avg Order Value:** Revenue per order
- **Growth Rate:** Percentage change vs. previous period

### Sales Trend Chart (Middle)
- Time-series line chart
- X-axis: Date
- Y-axis: Sales amount
- Hover for detailed values
- Zoom/pan enabled

### Product Performance Chart (Bottom)
- Top 10 products by revenue
- Horizontal bar chart
- Click to filter/drill-down

### Filters (Left Sidebar)
- **Date Range:** Select start and end dates
- **Category:** Filter by product line
- Charts update automatically on change

## Troubleshooting

### Server won't start

**Error:** `ModuleNotFoundError: No module named 'flasgger'`

**Solution:**
```bash
source .venv/bin/activate
pip install flasgger==0.9.7.1
```

### Dashboard shows no data

**Error:** Charts are empty or show "No data"

**Solution:**
```bash
# Regenerate sample data
python scripts/seed_duckdb.py
```

### JWT token expired

**Error:** `401 Unauthorized: Token has expired`

**Solution:**
1. Login again to get a new token
2. Or use refresh token: `POST /api/v1/auth/refresh`

### PostgreSQL connection error

**Error:** `could not connect to server`

**Solution:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if needed
sudo systemctl start postgresql
```

## Development Tips

### Hot Reload
- Flask auto-reloads on code changes (DEBUG=true)
- Just save the file, refresh browser

### View Logs
- Terminal shows all request logs
- Look for errors in red
- DEBUG level shows SQL queries

### Reset Everything
```bash
# Delete databases
rm data/analytical_cube.duckdb

# Regenerate
python scripts/seed_duckdb.py

# Restart server
python run.py
```

### Add New Endpoints
1. Create route in `app/routes/v1/`
2. Add Swagger docs (see `auth_routes.py` for examples)
3. Refresh Swagger UI
4. Test immediately

## Configuration

All settings in `.env` file (already configured):

```bash
ENVIRONMENT=development    # Enables Swagger UI
DEBUG=true                 # Auto-reload on changes
RATE_LIMIT_ENABLED=false   # Unlimited requests for dev
LOG_LEVEL=DEBUG           # Verbose logging
```

## Next Steps

### 1. Explore Swagger UI
- Test all authentication endpoints
- Try different query parameters
- View response schemas

### 2. Play with Dashboard
- Change date ranges
- Filter by category
- Examine chart interactivity

### 3. Add Your Data
Replace sample data with real data:
```bash
# Configure SQL Server in .env
SOURCES__SQL_SERVER__CREDENTIALS="mssql+pyodbc://..."

# Run ETL pipeline
python pipelines/ingest_sales_data.py
```

### 4. Customize Dashboard
Edit files:
- `app/dashboard/layouts/sales_dashboard.py`
- `app/dashboard/components/charts.py`
- `app/dashboard/callbacks/sales_callbacks.py`

## Resources

- **Full guide:** `LOCAL_DEVELOPMENT.md`
- **Project docs:** `CLAUDE.md`
- **API Explorer:** http://localhost:5000/apidocs/
- **Dashboard:** http://localhost:5000/dashboard/

## Summary

**What you have:**
- ✅ Fully functional REST API
- ✅ Interactive Swagger UI documentation
- ✅ Live Dash/Plotly dashboards
- ✅ 5000 sample sales transactions
- ✅ JWT authentication
- ✅ Role-based access control
- ✅ Health checks and metrics
- ✅ Auto-reload development server

**Enjoy coding!** 🚀

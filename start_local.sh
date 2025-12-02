#!/bin/bash
###############################################################################
# Privasee BI SaaS - Local Development Startup Script
###############################################################################
# This script automates the setup and startup of the application for local
# development. It handles dependency installation, database setup, sample
# data generation, and server startup.
#
# Usage:
#   ./start_local.sh [options]
#
# Options:
#   --skip-deps     Skip dependency installation
#   --skip-db       Skip PostgreSQL database check
#   --skip-seed     Skip DuckDB sample data generation
#   --fresh         Fresh start (reset databases)
#   --help          Show this help message
#
# Author: Development Team
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
DATA_DIR="$PROJECT_ROOT/data"
DUCKDB_FILE="$DATA_DIR/analytical_cube.duckdb"

# Flags
SKIP_DEPS=false
SKIP_DB=false
SKIP_SEED=false
FRESH_START=false

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

show_help() {
    cat << EOF
Privasee BI SaaS - Local Development Startup Script

Usage:
    ./start_local.sh [options]

Options:
    --skip-deps     Skip dependency installation
    --skip-db       Skip PostgreSQL database check
    --skip-seed     Skip DuckDB sample data generation
    --fresh         Fresh start (reset databases)
    --help          Show this help message

Examples:
    ./start_local.sh                 # Full setup and start
    ./start_local.sh --skip-deps     # Skip pip install
    ./start_local.sh --fresh         # Reset and fresh start

For more information, see LOCAL_DEVELOPMENT.md
EOF
    exit 0
}

###############################################################################
# Parse Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-seed)
            SKIP_SEED=true
            shift
            ;;
        --fresh)
            FRESH_START=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

###############################################################################
# Main Script
###############################################################################

print_header "Privasee BI SaaS - Local Development Setup"

# Step 1: Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION detected"

# Step 2: Create and activate virtual environment
print_info "Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

# Step 3: Install dependencies
if [ "$SKIP_DEPS" = false ]; then
    print_info "Installing dependencies..."
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1
    print_success "Dependencies installed"
else
    print_warning "Skipping dependency installation (--skip-deps)"
fi

# Step 4: Check PostgreSQL
if [ "$SKIP_DB" = false ]; then
    print_info "Checking PostgreSQL connection..."

    # Extract database URI from .env
    if [ -f "$PROJECT_ROOT/.env" ]; then
        DB_URI=$(grep "^AUTH_DB_URI=" "$PROJECT_ROOT/.env" | cut -d'=' -f2 | tr -d '"')

        # Try to connect with psql (optional check)
        if command -v psql &> /dev/null; then
            if psql "$DB_URI" -c "SELECT 1" &> /dev/null; then
                print_success "PostgreSQL connection successful"
            else
                print_warning "Could not connect to PostgreSQL"
                print_info "Database will be created when app starts"
            fi
        else
            print_warning "psql not found, skipping connection test"
        fi
    else
        print_error ".env file not found!"
        exit 1
    fi
else
    print_warning "Skipping PostgreSQL check (--skip-db)"
fi

# Step 5: Setup data directory
print_info "Setting up data directory..."
mkdir -p "$DATA_DIR"
print_success "Data directory ready"

# Step 6: Generate sample data (DuckDB)
if [ "$FRESH_START" = true ]; then
    print_info "Fresh start requested - removing existing DuckDB..."
    rm -f "$DUCKDB_FILE"
    print_success "Existing DuckDB removed"
fi

if [ "$SKIP_SEED" = false ]; then
    if [ ! -f "$DUCKDB_FILE" ] || [ "$FRESH_START" = true ]; then
        print_info "Generating sample data for DuckDB..."
        python "$PROJECT_ROOT/scripts/seed_duckdb.py"
        print_success "Sample data generated"
    else
        print_success "DuckDB already contains data (use --fresh to reset)"
    fi
else
    print_warning "Skipping sample data generation (--skip-seed)"
fi

# Step 7: Run database migrations
print_info "Checking database migrations..."
if flask db current &> /dev/null; then
    print_success "Database migrations up to date"
else
    print_warning "Migrations not applied (will auto-create tables)"
fi

# Step 8: Display access points
print_header "Setup Complete - Starting Server"

echo ""
print_info "Access points:"
echo "   Swagger UI:    http://localhost:5000/apidocs/"
echo "   Dashboard:     http://localhost:5000/dashboard/"
echo "   Health Check:  http://localhost:5000/health"
echo "   API Docs:      http://localhost:5000/api/v1/"
echo ""

print_info "Quick Start Guide:"
echo "   1. Open Swagger UI to test API endpoints"
echo "   2. Register a user: POST /api/v1/auth/register"
echo "   3. Copy access_token from response"
echo "   4. Click 'Authorize' in Swagger UI"
echo "   5. Test analytics: GET /api/v1/analytics/sales/summary"
echo "   6. View dashboard: http://localhost:5000/dashboard/"
echo ""

print_warning "Press Ctrl+C to stop the server"
echo ""

# Step 9: Start the development server
print_info "Starting Flask development server..."
echo ""

python "$PROJECT_ROOT/run.py"

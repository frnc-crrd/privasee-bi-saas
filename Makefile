# Makefile for Privasee BI SaaS
# Provides standardized commands for development, testing, and deployment operations.
#
# Usage:
#   make <target>
#
# Common Targets:
#   make help              Display all available targets
#   make setup-prod        Initialize production environment (first-time setup)
#   make deploy            Deploy application to production
#   make logs              View production application logs
#   make test              Run full test suite
#   make quality           Run code quality checks (linting, formatting, type checking)

.PHONY: help setup-prod deploy deploy-build stop logs test quality clean

# Default target: display help
.DEFAULT_GOAL := help

# Color output (ANSI escape codes)
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Project configuration
PROJECT_NAME := privasee-bi-saas
DOCKER_COMPOSE_PROD := docker-compose.prod.yml
ENV_FILE := .env.production

##@ General

help: ## Display this help message
	@echo ""
	@echo "$(BLUE)Privasee BI SaaS - Deployment & Development Commands$(NC)"
	@echo "$(BLUE)====================================================$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Production Deployment

setup-prod: ## Initialize production environment (first-time setup only)
	@echo "$(GREEN)Initializing production environment...$(NC)"
	@./scripts/setup_production.sh

generate-secrets: ## Generate production secrets (use --force to regenerate)
	@echo "$(GREEN)Generating production secrets...$(NC)"
	@./scripts/generate_secrets.sh

deploy: ## Deploy application (start containers without rebuild)
	@echo "$(GREEN)Deploying application to production...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)Deployment complete. Verify with 'make logs'$(NC)"

deploy-build: ## Deploy application (rebuild images before starting)
	@echo "$(GREEN)Building and deploying application...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) up -d --build
	@echo "$(GREEN)Build and deployment complete. Verify with 'make logs'$(NC)"

stop: ## Stop production containers
	@echo "$(YELLOW)Stopping production containers...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) down
	@echo "$(GREEN)Containers stopped successfully$(NC)"

restart: ## Restart production containers
	@echo "$(YELLOW)Restarting production containers...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) restart
	@echo "$(GREEN)Containers restarted successfully$(NC)"

logs: ## View production application logs (follow mode)
	@docker compose -f $(DOCKER_COMPOSE_PROD) logs -f app

logs-all: ## View all production service logs (follow mode)
	@docker compose -f $(DOCKER_COMPOSE_PROD) logs -f

status: ## Display status of production containers
	@docker compose -f $(DOCKER_COMPOSE_PROD) ps

health: ## Check application health endpoints
	@echo "$(BLUE)Checking application health...$(NC)"
	@curl -s http://localhost:8000/health/liveness | python3 -m json.tool || echo "$(RED)Health check failed$(NC)"
	@echo ""
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "$(RED)Health check failed$(NC)"

##@ Development

dev: ## Run development server (Flask debug mode)
	@echo "$(GREEN)Starting development server...$(NC)"
	@python run.py

shell: ## Open interactive shell in production container
	@docker compose -f $(DOCKER_COMPOSE_PROD) exec app /bin/bash

db-shell: ## Open PostgreSQL shell in production database
	@docker compose -f $(DOCKER_COMPOSE_PROD) exec db psql -U privasee_user -d privasee_prod

##@ Code Quality

quality: ## Run all code quality checks (linting, formatting, type checking)
	@echo "$(GREEN)Running code quality checks...$(NC)"
	@./run_checks.sh

lint: ## Run linter (Ruff)
	@echo "$(GREEN)Running Ruff linter...$(NC)"
	@ruff check .

lint-fix: ## Run linter with auto-fix
	@echo "$(GREEN)Running Ruff linter with auto-fix...$(NC)"
	@ruff check . --fix

format: ## Format code (Ruff formatter)
	@echo "$(GREEN)Formatting code...$(NC)"
	@ruff format .

format-check: ## Check code formatting without modification
	@echo "$(GREEN)Checking code formatting...$(NC)"
	@ruff format --check .

typecheck: ## Run type checker (Pyright)
	@echo "$(GREEN)Running Pyright type checker...$(NC)"
	@pyright

##@ Testing

test: ## Run full test suite
	@echo "$(GREEN)Running test suite...$(NC)"
	@pytest -v

test-cov: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	@pytest --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated at htmlcov/index.html$(NC)"

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	@pytest tests/unit -v

test-integration: ## Run integration tests only
	@echo "$(GREEN)Running integration tests...$(NC)"
	@pytest tests/integration -v

test-watch: ## Run tests in watch mode (re-run on file changes)
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	@pytest-watch

##@ Database Management

db-migrate: ## Run database migrations (Alembic)
	@echo "$(GREEN)Running database migrations...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) exec app alembic upgrade head

db-rollback: ## Rollback last database migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) exec app alembic downgrade -1

db-create-migration: ## Create new database migration (usage: make db-create-migration MSG="description")
	@echo "$(GREEN)Creating new migration...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) exec app alembic revision --autogenerate -m "$(MSG)"

db-backup: ## Create database backup
	@echo "$(GREEN)Creating database backup...$(NC)"
	@docker compose -f $(DOCKER_COMPOSE_PROD) exec db pg_dump -U privasee_user privasee_prod > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup created in backups/ directory$(NC)"

##@ Cleanup

clean: ## Remove temporary files and caches
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete$(NC)"

clean-docker: ## Remove Docker containers, volumes, and images
	@echo "$(RED)WARNING: This will remove all Docker containers, volumes, and images$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or press Enter to continue...$(NC)"
	@read confirm
	@docker compose -f $(DOCKER_COMPOSE_PROD) down -v --rmi all
	@echo "$(GREEN)Docker cleanup complete$(NC)"

##@ ETL Pipeline

etl-run: ## Run ETL pipeline (sales data ingestion)
	@echo "$(GREEN)Running ETL pipeline...$(NC)"
	@python pipelines/ingest_sales_data.py

##@ Monitoring

metrics: ## View Prometheus metrics endpoint
	@curl -s http://localhost:8000/metrics

prometheus: ## Open Prometheus dashboard in browser
	@echo "$(BLUE)Opening Prometheus at http://localhost:9090$(NC)"
	@xdg-open http://localhost:9090 2>/dev/null || open http://localhost:9090 2>/dev/null || echo "$(YELLOW)Open http://localhost:9090 manually$(NC)"

grafana: ## Open Grafana dashboard in browser
	@echo "$(BLUE)Opening Grafana at http://localhost:3000$(NC)"
	@xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || echo "$(YELLOW)Open http://localhost:3000 manually$(NC)"

##@ Documentation

docs-serve: ## Serve documentation locally (if using MkDocs or similar)
	@echo "$(BLUE)Documentation not yet configured$(NC)"

docs-build: ## Build static documentation
	@echo "$(BLUE)Documentation not yet configured$(NC)"

#!/usr/bin/env bash

################################################################################
# Script Name: setup_production.sh
# Description: Production environment initialization orchestrator.
#              Executes the complete setup workflow for first-time production
#              deployment, including secret generation, environment validation,
#              and infrastructure readiness checks.
#
# Usage: ./scripts/setup_production.sh [OPTIONS]
#
# Options:
#   --skip-secrets    Skip secret generation (use if already configured)
#   --skip-checks     Skip environment validation checks
#   --help            Display this help message
#
# Exit Codes:
#   0 - Success (environment ready for deployment)
#   1 - General error (setup failed)
#   2 - Validation failed (environment not ready)
#   3 - Dependency check failed
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env.production.template exists in project root
#   - Sufficient disk space for containers and volumes
#
# Workflow:
#   1. Validate system dependencies
#   2. Generate production secrets (if not skipped)
#   3. Validate environment configuration
#   4. Verify Docker network prerequisites
#   5. Display deployment readiness summary
#
# Author: Privasee DevOps Team
# Version: 1.0.0
################################################################################

set -euo pipefail

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly ENV_FILE="${PROJECT_ROOT}/.env.production"
readonly DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
readonly SECRETS_SCRIPT="${SCRIPT_DIR}/generate_secrets.sh"

# Flags
SKIP_SECRETS=false
SKIP_CHECKS=false

################################################################################
# Function: log_info
# Description: Logs informational messages to stdout.
#
# Args:
#   $1: Message to log
################################################################################
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

################################################################################
# Function: log_success
# Description: Logs success messages to stdout.
#
# Args:
#   $1: Message to log
################################################################################
log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

################################################################################
# Function: log_warning
# Description: Logs warning messages to stderr.
#
# Args:
#   $1: Message to log
################################################################################
log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

################################################################################
# Function: log_error
# Description: Logs error messages to stderr.
#
# Args:
#   $1: Message to log
################################################################################
log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

################################################################################
# Function: log_step
# Description: Logs step headers for major workflow stages.
#
# Args:
#   $1: Step description
################################################################################
log_step() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

################################################################################
# Function: show_help
# Description: Displays usage information and exits.
################################################################################
show_help() {
    cat << EOF
Production Environment Setup Orchestrator

Usage: $(basename "$0") [OPTIONS]

Description:
  Orchestrates the complete first-time production environment setup.
  Ensures all prerequisites are met before Docker container deployment.

Options:
  --skip-secrets    Skip automatic secret generation
  --skip-checks     Skip environment validation checks
  --help            Display this help message

Workflow:
  1. System dependency validation (Docker, Python, etc.)
  2. Production secret generation (cryptographically secure)
  3. Environment configuration validation
  4. Docker network prerequisite verification
  5. Deployment readiness summary

Exit Codes:
  0  Environment ready for deployment
  1  Setup failed (general error)
  2  Validation failed
  3  Dependencies missing

Examples:
  Standard first-time setup:
    ./scripts/setup_production.sh

  Setup with pre-existing secrets:
    ./scripts/setup_production.sh --skip-secrets

EOF
    exit 0
}

################################################################################
# Function: check_system_dependencies
# Description: Validates that all required system dependencies are installed.
#
# Returns:
#   0 if all dependencies are met
#   3 if dependencies are missing
################################################################################
check_system_dependencies() {
    log_step "Step 1: System Dependency Validation"

    local missing_deps=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    else
        log_success "Docker: $(docker --version)"
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        missing_deps+=("docker-compose")
    else
        log_success "Docker Compose: $(docker compose version)"
    fi

    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    else
        log_success "Python 3: $(python3 --version)"
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    else
        log_success "Git: $(git --version)"
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and retry"
        return 3
    fi

    log_success "All system dependencies satisfied"
    return 0
}

################################################################################
# Function: generate_production_secrets
# Description: Invokes the secrets generation script to create secure tokens.
#
# Returns:
#   0 on success
#   Exit code from generate_secrets.sh on failure
################################################################################
generate_production_secrets() {
    log_step "Step 2: Production Secret Generation"

    if [[ "${SKIP_SECRETS}" == true ]]; then
        log_warning "Secret generation skipped (--skip-secrets flag)"
        return 0
    fi

    if [[ ! -x "${SECRETS_SCRIPT}" ]]; then
        log_error "Secrets script not found or not executable: ${SECRETS_SCRIPT}"
        return 1
    fi

    log_info "Invoking secrets generation script..."
    "${SECRETS_SCRIPT}" || return $?

    log_success "Secret generation completed"
    return 0
}

################################################################################
# Function: validate_environment_file
# Description: Validates that .env.production exists and contains no placeholders.
#
# Returns:
#   0 if validation passes
#   2 if validation fails
################################################################################
validate_environment_file() {
    log_step "Step 3: Environment Configuration Validation"

    if [[ "${SKIP_CHECKS}" == true ]]; then
        log_warning "Environment validation skipped (--skip-checks flag)"
        return 0
    fi

    if [[ ! -f "${ENV_FILE}" ]]; then
        log_error "Environment file not found: ${ENV_FILE}"
        log_error "Run without --skip-secrets to generate it"
        return 2
    fi

    log_success "Environment file exists: ${ENV_FILE}"

    # Check for placeholders
    local placeholder_count
    placeholder_count=$(grep -c "PEGAR_VALOR_GENERADO_AQUI" "${ENV_FILE}" 2>/dev/null || true)

    if [[ ${placeholder_count} -gt 0 ]]; then
        log_error "Environment file contains ${placeholder_count} unresolved placeholders"
        log_error "Run generate_secrets.sh to populate secrets"
        return 2
    fi

    log_success "No placeholders detected in environment file"

    # Validate critical variables
    local critical_vars=("SECRET_KEY" "JWT_SECRET_KEY" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
    local missing_vars=()

    for var in "${critical_vars[@]}"; do
        if ! grep -q "^${var}=" "${ENV_FILE}"; then
            missing_vars+=("${var}")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing critical environment variables: ${missing_vars[*]}"
        return 2
    fi

    log_success "All critical environment variables present"
    return 0
}

################################################################################
# Function: validate_docker_prerequisites
# Description: Verifies Docker daemon is running and compose file exists.
#
# Returns:
#   0 if validation passes
#   2 if validation fails
################################################################################
validate_docker_prerequisites() {
    log_step "Step 4: Docker Infrastructure Validation"

    if [[ "${SKIP_CHECKS}" == true ]]; then
        log_warning "Docker validation skipped (--skip-checks flag)"
        return 0
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        log_error "Start Docker service and retry"
        return 2
    fi

    log_success "Docker daemon is running"

    # Check compose file
    if [[ ! -f "${DOCKER_COMPOSE_FILE}" ]]; then
        log_error "Docker Compose file not found: ${DOCKER_COMPOSE_FILE}"
        return 2
    fi

    log_success "Docker Compose file exists: ${DOCKER_COMPOSE_FILE}"

    # Validate compose file syntax
    if ! docker compose -f "${DOCKER_COMPOSE_FILE}" config &> /dev/null; then
        log_error "Docker Compose file has syntax errors"
        log_error "Run 'docker compose -f ${DOCKER_COMPOSE_FILE} config' to debug"
        return 2
    fi

    log_success "Docker Compose file syntax valid"

    return 0
}

################################################################################
# Function: display_deployment_summary
# Description: Displays final summary and next steps for deployment.
################################################################################
display_deployment_summary() {
    log_step "Production Environment Ready"

    cat << EOF

${GREEN}Production environment setup completed successfully.${NC}

${CYAN}Environment Summary:${NC}
  - Configuration File: ${ENV_FILE}
  - Docker Compose:     ${DOCKER_COMPOSE_FILE}
  - Secrets:            Generated and secured (600 permissions)

${CYAN}Next Steps:${NC}

  1. Review configuration:
     ${YELLOW}cat ${ENV_FILE}${NC}

  2. Build Docker images:
     ${YELLOW}docker compose -f docker-compose.prod.yml build${NC}

  3. Start production stack:
     ${YELLOW}docker compose -f docker-compose.prod.yml up -d${NC}

  4. Verify health:
     ${YELLOW}curl http://localhost:8000/health${NC}

  5. View logs:
     ${YELLOW}docker compose -f docker-compose.prod.yml logs -f app${NC}

${CYAN}Security Reminders:${NC}
  - Never commit .env.production to version control
  - Backup secrets to secure vault (e.g., 1Password, Vault)
  - Rotate secrets periodically (recommended: every 90 days)
  - Monitor access logs for unauthorized access attempts

${GREEN}Deployment authorized. Proceed with confidence.${NC}

EOF
}

################################################################################
# Function: main
# Description: Main execution flow with error handling and exit code management.
################################################################################
main() {
    log_info "Production Environment Setup Orchestrator v1.0.0"
    log_info "================================================="

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-secrets)
                SKIP_SECRETS=true
                shift
                ;;
            --skip-checks)
                SKIP_CHECKS=true
                shift
                ;;
            --help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done

    # Execute workflow
    check_system_dependencies || exit 3

    generate_production_secrets || exit $?

    validate_environment_file || exit 2

    validate_docker_prerequisites || exit 2

    display_deployment_summary

    exit 0
}

# Execute main function
main "$@"

#!/usr/bin/env bash

################################################################################
# Script Name: generate_secrets.sh
# Description: Cryptographically secure secret generation for production environment.
#              Generates and injects secrets into .env.production file using
#              Python's secrets module (CSPRNG-based). Implements idempotency
#              to prevent accidental overwrite of existing production secrets.
#
# Usage: ./scripts/generate_secrets.sh [OPTIONS]
#
# Options:
#   --force    Force regeneration of secrets even if they already exist
#   --help     Display this help message
#
# Exit Codes:
#   0 - Success (secrets generated or already exist)
#   1 - General error (missing dependencies, file not found)
#   2 - Secrets already exist (use --force to override)
#   3 - Python not available or secrets module unavailable
#
# Security Context:
#   - Must be run BEFORE Docker containers are initialized
#   - Requires .env.production.template to exist
#   - Generates cryptographically secure random tokens
#   - Creates backup before modification
#
# Author: Privasee DevOps Team
# Version: 1.0.0
################################################################################

set -euo pipefail

# Color codes for output (production-safe, will not break log aggregation)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly TEMPLATE_FILE="${PROJECT_ROOT}/.env.production.template"
readonly TARGET_FILE="${PROJECT_ROOT}/.env.production"
readonly BACKUP_DIR="${PROJECT_ROOT}/.env.backups"
readonly PLACEHOLDER_TEXT="PEGAR_VALOR_GENERADO_AQUI"

# Flags
FORCE_REGENERATE=false

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
# Function: show_help
# Description: Displays usage information and exits.
################################################################################
show_help() {
    cat << EOF
Production Secrets Generation Utility

Usage: $(basename "$0") [OPTIONS]

Description:
  Generates cryptographically secure secrets for production deployment.
  Uses Python's secrets module to generate CSPRNG-based random tokens.
  Implements idempotency to prevent accidental secret regeneration.

Options:
  --force    Force regeneration of secrets (overwrites existing)
  --help     Display this help message

Exit Codes:
  0  Success
  1  General error
  2  Secrets already exist (use --force)
  3  Python dependencies unavailable

Examples:
  Initial setup:
    ./scripts/generate_secrets.sh

  Force regeneration (CAUTION - invalidates existing sessions):
    ./scripts/generate_secrets.sh --force

EOF
    exit 0
}

################################################################################
# Function: check_dependencies
# Description: Validates that required dependencies are available.
#
# Returns:
#   0 if all dependencies are met
#   3 if dependencies are missing
################################################################################
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed or not in PATH"
        return 3
    fi

    if ! python3 -c "import secrets" 2>/dev/null; then
        log_error "Python secrets module is not available"
        return 3
    fi

    log_success "All dependencies satisfied"
    return 0
}

################################################################################
# Function: check_idempotency
# Description: Verifies if secrets have already been generated.
#              Prevents accidental overwrite unless --force is specified.
#
# Returns:
#   0 if regeneration should proceed
#   2 if secrets exist and --force not specified
################################################################################
check_idempotency() {
    if [[ ! -f "${TARGET_FILE}" ]]; then
        log_info "Target file does not exist. Will create from template."
        return 0
    fi

    local placeholder_count
    placeholder_count=$(grep -c "${PLACEHOLDER_TEXT}" "${TARGET_FILE}" 2>/dev/null || true)

    if [[ ${placeholder_count} -eq 0 ]]; then
        if [[ "${FORCE_REGENERATE}" == false ]]; then
            log_warning "Secrets already exist in ${TARGET_FILE}"
            log_warning "Use --force to regenerate (CAUTION: invalidates existing sessions)"
            return 2
        else
            log_warning "Force flag detected. Regenerating secrets..."
            return 0
        fi
    fi

    log_info "Placeholders detected. Proceeding with secret generation."
    return 0
}

################################################################################
# Function: create_backup
# Description: Creates timestamped backup of existing .env.production file.
#
# Returns:
#   0 on success
#   1 on failure
################################################################################
create_backup() {
    if [[ ! -f "${TARGET_FILE}" ]]; then
        log_info "No existing file to backup"
        return 0
    fi

    mkdir -p "${BACKUP_DIR}"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/.env.production.${timestamp}.backup"

    if cp "${TARGET_FILE}" "${backup_file}"; then
        log_success "Backup created: ${backup_file}"
        return 0
    else
        log_error "Failed to create backup"
        return 1
    fi
}

################################################################################
# Function: generate_secret
# Description: Generates a cryptographically secure random token.
#
# Args:
#   $1: Length of the token (in bytes, base64url encoded)
#
# Returns:
#   Prints the generated secret to stdout
################################################################################
generate_secret() {
    local length="$1"
    python3 -c "import secrets; print(secrets.token_urlsafe(${length}))"
}

################################################################################
# Function: generate_and_inject_secrets
# Description: Generates all required secrets and injects them into the
#              .env.production file using secure in-place substitution.
#
# Returns:
#   0 on success
#   1 on failure
################################################################################
generate_and_inject_secrets() {
    log_info "Generating cryptographically secure secrets..."

    # Generate secrets
    local SECRET_KEY
    local JWT_SECRET_KEY
    local POSTGRES_PASSWORD
    local REDIS_PASSWORD
    local GRAFANA_PASSWORD

    SECRET_KEY=$(generate_secret 32)
    JWT_SECRET_KEY=$(generate_secret 32)
    POSTGRES_PASSWORD=$(generate_secret 24)
    REDIS_PASSWORD=$(generate_secret 24)
    GRAFANA_PASSWORD=$(generate_secret 24)

    log_info "Secrets generated successfully"

    # Create target from template if it does not exist
    if [[ ! -f "${TARGET_FILE}" ]]; then
        if [[ ! -f "${TEMPLATE_FILE}" ]]; then
            log_error "Template file not found: ${TEMPLATE_FILE}"
            return 1
        fi
        cp "${TEMPLATE_FILE}" "${TARGET_FILE}"
        log_info "Created ${TARGET_FILE} from template"
    fi

    log_info "Injecting secrets into ${TARGET_FILE}..."

    # Perform in-place substitution using sed
    # Using | as delimiter to avoid conflicts with / in base64url encoding
    sed -i "s|SECRET_KEY=${PLACEHOLDER_TEXT}|SECRET_KEY=${SECRET_KEY}|" "${TARGET_FILE}"
    sed -i "s|JWT_SECRET_KEY=${PLACEHOLDER_TEXT}|JWT_SECRET_KEY=${JWT_SECRET_KEY}|" "${TARGET_FILE}"
    sed -i "s|POSTGRES_PASSWORD=${PLACEHOLDER_TEXT}|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|g" "${TARGET_FILE}"
    sed -i "s|REDIS_PASSWORD=${PLACEHOLDER_TEXT}|REDIS_PASSWORD=${REDIS_PASSWORD}|g" "${TARGET_FILE}"
    sed -i "s|GRAFANA_ADMIN_PASSWORD=${PLACEHOLDER_TEXT}|GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASSWORD}|" "${TARGET_FILE}"

    # Also replace passwords within connection strings
    sed -i "s|postgresql://privasee_user:${PLACEHOLDER_TEXT}@|postgresql://privasee_user:${POSTGRES_PASSWORD}@|" "${TARGET_FILE}"
    sed -i "s|redis://:${PLACEHOLDER_TEXT}@|redis://:${REDIS_PASSWORD}@|" "${TARGET_FILE}"

    log_success "Secrets injected successfully"
    return 0
}

################################################################################
# Function: validate_result
# Description: Validates that all placeholders have been replaced with secrets.
#
# Returns:
#   0 if validation passes
#   1 if placeholders remain
################################################################################
validate_result() {
    log_info "Validating secret injection..."

    local remaining_placeholders
    remaining_placeholders=$(grep -c "${PLACEHOLDER_TEXT}" "${TARGET_FILE}" 2>/dev/null || true)

    if [[ ${remaining_placeholders} -gt 0 ]]; then
        log_error "Validation failed: ${remaining_placeholders} placeholders remain"
        log_error "Manual intervention required"
        return 1
    fi

    log_success "Validation passed: All secrets generated successfully"
    return 0
}

################################################################################
# Function: set_secure_permissions
# Description: Sets restrictive file permissions on .env.production to prevent
#              unauthorized access (owner read/write only).
################################################################################
set_secure_permissions() {
    log_info "Setting secure file permissions..."

    chmod 600 "${TARGET_FILE}"

    log_success "File permissions set to 600 (owner read/write only)"
}

################################################################################
# Function: main
# Description: Main execution flow with error handling and exit code management.
################################################################################
main() {
    log_info "Production Secrets Generation Utility v1.0.0"
    log_info "=============================================="

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force)
                FORCE_REGENERATE=true
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
    check_dependencies || exit 3

    check_idempotency || exit 2

    create_backup || {
        log_error "Backup creation failed. Aborting for safety."
        exit 1
    }

    generate_and_inject_secrets || {
        log_error "Secret generation failed"
        exit 1
    }

    validate_result || {
        log_error "Validation failed"
        exit 1
    }

    set_secure_permissions

    log_success "=============================================="
    log_success "Production secrets generated successfully"
    log_success "File: ${TARGET_FILE}"
    log_success "Backups stored in: ${BACKUP_DIR}"
    log_success "You may now proceed with Docker container initialization"

    exit 0
}

# Execute main function
main "$@"

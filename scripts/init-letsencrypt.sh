#!/usr/bin/env bash

################################################################################
# Script Name: init-letsencrypt.sh
# Description: Initialize Let's Encrypt SSL certificates for production deployment.
#              Automates certificate acquisition using Certbot with webroot validation.
#
# Usage: ./scripts/init-letsencrypt.sh DOMAIN EMAIL [--staging]
#
# Arguments:
#   DOMAIN      Primary domain for SSL certificate (e.g., privasee.com)
#   EMAIL       Email for certificate expiry notifications
#   --staging   Optional flag to use Let's Encrypt staging server (for testing)
#
# Examples:
#   ./scripts/init-letsencrypt.sh privasee.com admin@privasee.com
#   ./scripts/init-letsencrypt.sh test.privasee.com admin@privasee.com --staging
#
# Prerequisites:
#   - Docker and docker-compose installed
#   - Domain DNS pointing to server IP
#   - Ports 80 and 443 accessible
#   - Nginx container running
#
# Exit Codes:
#   0 - Success (certificates obtained)
#   1 - Invalid arguments or prerequisites not met
#   2 - Certificate acquisition failed
#
# Author: Privasee DevOps Team
# Version: 1.0.0
################################################################################

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

################################################################################
# Function: log_info
# Description: Logs informational messages to stdout
################################################################################
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

################################################################################
# Function: log_success
# Description: Logs success messages to stdout
################################################################################
log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

################################################################################
# Function: log_warning
# Description: Logs warning messages to stderr
################################################################################
log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

################################################################################
# Function: log_error
# Description: Logs error messages to stderr
################################################################################
log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

################################################################################
# Function: show_help
# Description: Displays usage information and exits
################################################################################
show_help() {
    cat <<EOF
Usage: $0 DOMAIN EMAIL [--staging]

Initialize Let's Encrypt SSL certificates for production deployment.

Arguments:
  DOMAIN      Primary domain for SSL certificate (e.g., privasee.com)
  EMAIL       Email for certificate expiry notifications
  --staging   Optional: Use Let's Encrypt staging server (for testing)

Examples:
  $0 privasee.com admin@privasee.com
  $0 test.privasee.com admin@privasee.com --staging

Prerequisites:
  - Docker and docker-compose installed
  - Domain DNS pointing to server IP
  - Ports 80 and 443 accessible
  - Nginx container running

EOF
    exit 0
}

################################################################################
# Parse arguments
################################################################################
if [[ $# -lt 2 ]]; then
    log_error "Missing required arguments"
    show_help
fi

DOMAIN="$1"
EMAIL="$2"
STAGING=""

if [[ "${3:-}" == "--staging" ]]; then
    STAGING="--staging"
    log_warning "Using Let's Encrypt STAGING server (certificates will not be trusted)"
fi

################################################################################
# Validate prerequisites
################################################################################
log_info "Validating prerequisites..."

# Check if docker-compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
    log_error "docker-compose.prod.yml not found at: $COMPOSE_FILE"
    exit 1
fi

# Check if nginx container is running
if ! docker ps --format '{{.Names}}' | grep -q "privasee-nginx"; then
    log_error "Nginx container is not running. Start it with:"
    log_error "  docker-compose -f docker-compose.prod.yml up -d nginx"
    exit 1
fi

log_success "Prerequisites validated"

################################################################################
# Create dummy certificate for initial nginx start
################################################################################
log_info "Creating dummy certificate for ${DOMAIN}..."

docker-compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '/etc/letsencrypt/live/${DOMAIN}/privkey.pem' \
    -out '/etc/letsencrypt/live/${DOMAIN}/fullchain.pem' \
    -subj '/CN=localhost'" certbot

log_success "Dummy certificate created"

################################################################################
# Reload nginx with dummy certificate
################################################################################
log_info "Reloading nginx configuration..."

docker-compose -f "$COMPOSE_FILE" exec nginx nginx -s reload

log_success "Nginx reloaded"

################################################################################
# Delete dummy certificate
################################################################################
log_info "Removing dummy certificate..."

docker-compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/${DOMAIN} && \
  rm -rf /etc/letsencrypt/archive/${DOMAIN} && \
  rm -rf /etc/letsencrypt/renewal/${DOMAIN}.conf" certbot

log_success "Dummy certificate removed"

################################################################################
# Request real certificate from Let's Encrypt
################################################################################
log_info "Requesting Let's Encrypt certificate for ${DOMAIN}..."

docker-compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  certbot certonly --webroot --webroot-path=/var/www/certbot \
    $STAGING \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d $DOMAIN" certbot

if [[ $? -ne 0 ]]; then
    log_error "Failed to obtain SSL certificate"
    exit 2
fi

log_success "SSL certificate obtained successfully"

################################################################################
# Reload nginx with real certificate
################################################################################
log_info "Reloading nginx with production certificate..."

docker-compose -f "$COMPOSE_FILE" exec nginx nginx -s reload

log_success "Nginx reloaded with SSL certificate"

################################################################################
# Display certificate information
################################################################################
log_info "Certificate information:"

docker-compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  certbot certificates" certbot

################################################################################
# Final instructions
################################################################################
cat <<EOF

${GREEN}========================================================================
SSL CERTIFICATE SETUP COMPLETE
========================================================================${NC}

Domain:     $DOMAIN
Email:      $EMAIL
Status:     Active

${BLUE}Certificate Details:${NC}
- Location:  /etc/letsencrypt/live/${DOMAIN}/
- Validity:  90 days
- Auto-renewal: Every 12 hours (via certbot container)

${BLUE}Next Steps:${NC}
1. Update nginx configuration to use HTTPS
2. Test HTTPS access: https://${DOMAIN}
3. Verify auto-renewal: docker logs privasee-certbot

${BLUE}Manual Renewal (if needed):${NC}
  docker-compose -f docker-compose.prod.yml exec certbot certbot renew

${GREEN}========================================================================${NC}

EOF

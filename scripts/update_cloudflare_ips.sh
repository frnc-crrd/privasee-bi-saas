#!/usr/bin/env bash

################################################################################
# Script Name: update_cloudflare_ips.sh
# Description: Automatically updates Cloudflare IP ranges in Nginx configuration.
#              Fetches the latest IP ranges from Cloudflare's official API and
#              regenerates the real IP configuration file.
#
# Usage: ./scripts/update_cloudflare_ips.sh [OPTIONS]
#
# Options:
#   --dry-run  Show changes without applying them
#   --force    Skip confirmation prompt
#   --help     Display this help message
#
# Exit Codes:
#   0 - Success (IP ranges updated)
#   1 - General error (download failed, permission denied)
#   2 - No changes detected (IP ranges already up-to-date)
#   3 - Dependencies unavailable
#
# Maintenance Schedule:
#   - Recommended frequency: Weekly (automated via cron)
#   - Cloudflare updates IP ranges infrequently (quarterly to annually)
#   - Manual execution required after Cloudflare network expansion announcements
#
# Security Context:
#   - Must be run with sufficient permissions to write to nginx/conf.d/
#   - Validates downloaded IP ranges before applying (CIDR format validation)
#   - Creates backup before modification
#   - Requires Nginx configuration reload after update
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
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly NGINX_CONF_DIR="${PROJECT_ROOT}/nginx/conf.d"
readonly CONFIG_FILE="${NGINX_CONF_DIR}/00-cloudflare-real-ip.conf"
readonly BACKUP_DIR="${PROJECT_ROOT}/.cloudflare-backups"
readonly CLOUDFLARE_IPV4_URL="https://www.cloudflare.com/ips-v4"
readonly CLOUDFLARE_IPV6_URL="https://www.cloudflare.com/ips-v6"

# Flags
DRY_RUN=false
FORCE=false

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
Cloudflare IP Ranges Update Utility

Usage: $(basename "$0") [OPTIONS]

Description:
  Automatically updates Cloudflare IP ranges in Nginx real IP configuration.
  Fetches the latest IP ranges from Cloudflare's official endpoints and
  regenerates the 00-cloudflare-real-ip.conf file.

Options:
  --dry-run    Show changes without applying them
  --force      Skip confirmation prompt (for automation)
  --help       Display this help message

Exit Codes:
  0  Success (IP ranges updated)
  1  General error (download failed, permission denied)
  2  No changes detected (already up-to-date)
  3  Dependencies unavailable

Examples:
  Check for updates without applying:
    ./scripts/update_cloudflare_ips.sh --dry-run

  Update IP ranges with confirmation:
    ./scripts/update_cloudflare_ips.sh

  Update IP ranges automatically (cron):
    ./scripts/update_cloudflare_ips.sh --force

Cron Schedule:
  # Update Cloudflare IPs weekly (Sunday at 2 AM)
  0 2 * * 0 /path/to/scripts/update_cloudflare_ips.sh --force && docker compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload

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

    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v grep &> /dev/null; then
        missing_deps+=("grep")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        return 3
    fi

    log_success "All dependencies satisfied"
    return 0
}

################################################################################
# Function: fetch_cloudflare_ips
# Description: Downloads current Cloudflare IP ranges from official endpoints.
#
# Returns:
#   0 on success
#   1 on failure
################################################################################
fetch_cloudflare_ips() {
    log_info "Fetching Cloudflare IP ranges..."

    local ipv4_ranges ipv6_ranges

    # Fetch IPv4 ranges
    if ! ipv4_ranges=$(curl -sf --max-time 10 "${CLOUDFLARE_IPV4_URL}"); then
        log_error "Failed to download IPv4 ranges from ${CLOUDFLARE_IPV4_URL}"
        return 1
    fi

    # Fetch IPv6 ranges
    if ! ipv6_ranges=$(curl -sf --max-time 10 "${CLOUDFLARE_IPV6_URL}"); then
        log_error "Failed to download IPv6 ranges from ${CLOUDFLARE_IPV6_URL}"
        return 1
    fi

    # Validate format (basic CIDR validation)
    if ! echo "$ipv4_ranges" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'; then
        log_error "Invalid IPv4 CIDR format detected"
        return 1
    fi

    if ! echo "$ipv6_ranges" | grep -Eq '^[0-9a-f:]+/[0-9]{1,3}$'; then
        log_error "Invalid IPv6 CIDR format detected"
        return 1
    fi

    log_success "Successfully fetched Cloudflare IP ranges"

    # Export for use in other functions
    CLOUDFLARE_IPV4="$ipv4_ranges"
    CLOUDFLARE_IPV6="$ipv6_ranges"

    return 0
}

################################################################################
# Function: generate_config
# Description: Generates new Nginx configuration with updated IP ranges.
#
# Returns:
#   0 on success
################################################################################
generate_config() {
    log_info "Generating updated configuration..."

    local ipv4_count ipv6_count
    ipv4_count=$(echo "$CLOUDFLARE_IPV4" | wc -l)
    ipv6_count=$(echo "$CLOUDFLARE_IPV6" | wc -l)

    log_info "IPv4 ranges: ${ipv4_count}"
    log_info "IPv6 ranges: ${ipv6_count}"

    # Generate set_real_ip_from directives for IPv4
    local ipv4_directives=""
    while IFS= read -r ip; do
        ipv4_directives+="set_real_ip_from ${ip};\n"
    done <<< "$CLOUDFLARE_IPV4"

    # Generate set_real_ip_from directives for IPv6
    local ipv6_directives=""
    while IFS= read -r ip; do
        ipv6_directives+="set_real_ip_from ${ip};\n"
    done <<< "$CLOUDFLARE_IPV6"

    # Read template and inject IP ranges
    cat > "${CONFIG_FILE}.tmp" << 'EOF'
# ==============================================================================
# Cloudflare Real IP Configuration
# ==============================================================================
#
# Purpose:
#   Configures Nginx to correctly identify the true originating IP address of
#   clients when traffic is proxied through Cloudflare's global WAF/CDN network.
#
# Architecture:
#   User → Cloudflare (WAF/CDN) → Nginx (Reverse Proxy) → Application
#
# IMPORTANT: This file is auto-generated. Do not edit manually.
# To update Cloudflare IP ranges, run: ./scripts/update_cloudflare_ips.sh
#
EOF

    echo "# Last Updated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "${CONFIG_FILE}.tmp"
    echo "# IPv4 Ranges: ${ipv4_count} | IPv6 Ranges: ${ipv6_count}" >> "${CONFIG_FILE}.tmp"
    echo "" >> "${CONFIG_FILE}.tmp"

    cat >> "${CONFIG_FILE}.tmp" << 'EOF'

# ==============================================================================
# Real IP Header Configuration
# ==============================================================================

real_ip_header CF-Connecting-IP;
real_ip_recursive on;

# ==============================================================================
# Cloudflare IPv4 Address Ranges
# ==============================================================================

EOF

    echo -e "${ipv4_directives}" >> "${CONFIG_FILE}.tmp"

    cat >> "${CONFIG_FILE}.tmp" << 'EOF'

# ==============================================================================
# Cloudflare IPv6 Address Ranges
# ==============================================================================

EOF

    echo -e "${ipv6_directives}" >> "${CONFIG_FILE}.tmp"

    log_success "Configuration generated successfully"
    return 0
}

################################################################################
# Function: create_backup
# Description: Creates timestamped backup of existing configuration.
#
# Returns:
#   0 on success
#   1 on failure
################################################################################
create_backup() {
    if [[ ! -f "${CONFIG_FILE}" ]]; then
        log_info "No existing configuration to backup"
        return 0
    fi

    mkdir -p "${BACKUP_DIR}"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/00-cloudflare-real-ip.conf.${timestamp}.backup"

    if cp "${CONFIG_FILE}" "${backup_file}"; then
        log_success "Backup created: ${backup_file}"
        return 0
    else
        log_error "Failed to create backup"
        return 1
    fi
}

################################################################################
# Function: apply_changes
# Description: Applies the new configuration file.
#
# Returns:
#   0 on success
#   1 on failure
################################################################################
apply_changes() {
    if [[ "${DRY_RUN}" == true ]]; then
        log_warning "Dry-run mode: Changes not applied"
        log_info "Diff preview:"
        diff -u "${CONFIG_FILE}" "${CONFIG_FILE}.tmp" || true
        rm -f "${CONFIG_FILE}.tmp"
        return 0
    fi

    if mv "${CONFIG_FILE}.tmp" "${CONFIG_FILE}"; then
        log_success "Configuration updated: ${CONFIG_FILE}"
        return 0
    else
        log_error "Failed to apply changes"
        return 1
    fi
}

################################################################################
# Function: main
# Description: Main execution flow with error handling and exit code management.
################################################################################
main() {
    log_info "Cloudflare IP Ranges Update Utility v1.0.0"
    log_info "============================================"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
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

    fetch_cloudflare_ips || exit 1

    generate_config || exit 1

    create_backup || {
        log_error "Backup creation failed. Aborting for safety."
        exit 1
    }

    # Confirmation prompt (unless --force)
    if [[ "${FORCE}" == false ]] && [[ "${DRY_RUN}" == false ]]; then
        echo ""
        log_warning "This will update the Nginx Cloudflare IP configuration."
        log_warning "After updating, you must reload Nginx for changes to take effect."
        echo ""
        read -p "Proceed with update? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Update cancelled by user"
            rm -f "${CONFIG_FILE}.tmp"
            exit 0
        fi
    fi

    apply_changes || exit 1

    log_success "============================================"
    log_success "Cloudflare IP ranges updated successfully"
    log_success "Configuration file: ${CONFIG_FILE}"
    log_success "Backup directory: ${BACKUP_DIR}"

    if [[ "${DRY_RUN}" == false ]]; then
        echo ""
        log_warning "IMPORTANT: Reload Nginx to apply changes:"
        echo ""
        echo "  ${YELLOW}docker compose -f docker-compose.prod.yml exec nginx nginx -s reload${NC}"
        echo ""
        echo "  Or restart the container:"
        echo "  ${YELLOW}docker compose -f docker-compose.prod.yml restart nginx${NC}"
        echo ""
    fi

    exit 0
}

# Execute main function
main "$@"

# Production Deployment Scripts

This directory contains operational scripts for production environment setup and maintenance.

## Overview

The deployment automation suite consists of two primary scripts that ensure secure, idempotent, and auditable production environment initialization.

### Script Inventory

| Script | Purpose | Invocation Context |
|--------|---------|-------------------|
| `generate_secrets.sh` | Cryptographically secure secret generation | First-time setup, secret rotation |
| `setup_production.sh` | Production environment orchestrator | Initial deployment, environment validation |

## Security Architecture

### Secret Generation Strategy

Production secrets are generated using Python's `secrets` module, which provides cryptographically secure random number generation (CSPRNG) backed by the operating system's entropy sources.

**Key Properties:**
- Token length: 32 bytes for authentication keys (base64url encoded)
- Token length: 24 bytes for database passwords (base64url encoded)
- Entropy source: `/dev/urandom` on Linux, `CryptGenRandom` on Windows
- Output format: URL-safe base64 encoding (RFC 4648 Section 5)

### Idempotency Guarantees

The secret generation script implements strict idempotency controls:

1. **Pre-execution Check:** Scans `.env.production` for placeholder strings
2. **Conditional Execution:** Only generates secrets if placeholders are detected
3. **Force Override:** Requires explicit `--force` flag to regenerate existing secrets
4. **Backup Mechanism:** Creates timestamped backups before any modification

**Rationale:** Prevents accidental secret regeneration, which would invalidate:
- Active user sessions (JWT tokens signed with old key)
- Database connections (password mismatch)
- Redis connections (authentication failure)

### File Permissions

Generated `.env.production` file is automatically secured with:
- Permission mask: `600` (owner read/write only)
- Owner: Current user executing the script
- Group/Other: No access

## Usage

### First-Time Production Setup

For initial deployment on a new production server:

```bash
# Standard setup (recommended)
./scripts/setup_production.sh
```

This orchestrator will:
1. Validate system dependencies (Docker, Python, Git)
2. Generate production secrets automatically
3. Validate environment configuration
4. Verify Docker prerequisites
5. Display deployment readiness summary

### Manual Secret Generation

If you need to generate secrets independently:

```bash
# Generate secrets (safe - will not overwrite existing)
./scripts/generate_secrets.sh

# Force regeneration (CAUTION: invalidates active sessions)
./scripts/generate_secrets.sh --force
```

### Setup with Pre-existing Secrets

If you have manually configured `.env.production`:

```bash
# Skip secret generation, validate environment only
./scripts/setup_production.sh --skip-secrets
```

### Validation Only

To validate environment without making changes:

```bash
# Validation dry-run
./scripts/setup_production.sh --skip-secrets --skip-checks
```

## Script Exit Codes

All scripts follow POSIX exit code conventions for automation compatibility.

### generate_secrets.sh

| Exit Code | Meaning | Resolution |
|-----------|---------|------------|
| `0` | Success (secrets generated or already exist) | Proceed to deployment |
| `1` | General error (file not found, permission denied) | Check error message, verify file paths |
| `2` | Secrets already exist (protection mechanism) | Use `--force` if regeneration is intentional |
| `3` | Python dependencies unavailable | Install Python 3 with secrets module |

### setup_production.sh

| Exit Code | Meaning | Resolution |
|-----------|---------|------------|
| `0` | Environment ready for deployment | Execute `docker compose up` |
| `1` | Setup failed (general error) | Review error logs, check prerequisites |
| `2` | Validation failed (environment not ready) | Fix validation errors and retry |
| `3` | System dependencies missing | Install missing dependencies |

## Workflow Integration

### CI/CD Pipeline Integration

For automated deployments in CI/CD pipelines:

```yaml
# Example: GitLab CI/CD
deploy:production:
  stage: deploy
  script:
    - ./scripts/setup_production.sh --skip-checks
    - docker compose -f docker-compose.prod.yml up -d --build
  only:
    - main
  when: manual
```

### Makefile Integration

The scripts are integrated into the project Makefile for convenience:

```bash
# First-time setup
make setup-prod

# Generate secrets manually
make generate-secrets

# Deploy application
make deploy-build
```

See `Makefile` in project root for complete command reference.

## Backup Management

### Automatic Backups

Every modification to `.env.production` triggers automatic backup creation:

**Backup Location:** `.env.backups/.env.production.<timestamp>.backup`

**Timestamp Format:** `YYYYMMDD_HHMMSS` (e.g., `20250127_143052`)

### Manual Backup Restoration

To restore from backup:

```bash
# List available backups
ls -lh .env.backups/

# Restore specific backup
cp .env.backups/.env.production.20250127_143052.backup .env.production

# Verify restoration
grep -c "PEGAR_VALOR_GENERADO_AQUI" .env.production
# Should output: 0
```

## Secret Rotation

Production secrets should be rotated periodically for security compliance.

**Recommended Rotation Schedule:**
- Authentication keys (SECRET_KEY, JWT_SECRET_KEY): Every 90 days
- Database passwords: Every 180 days
- Redis passwords: Every 180 days
- Grafana admin password: On security incident or personnel change

### Rotation Procedure

```bash
# 1. Backup current configuration
cp .env.production .env.production.pre-rotation

# 2. Force regenerate secrets
./scripts/generate_secrets.sh --force

# 3. Rebuild containers with new secrets
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# 4. Verify health
curl http://localhost:8000/health

# 5. Archive old secrets securely (e.g., to password vault)
```

**Note:** Secret rotation will invalidate all active user sessions.

## Troubleshooting

### Issue: "Python secrets module not available"

**Cause:** Python installation is missing or incomplete

**Resolution:**
```bash
# Verify Python installation
python3 --version

# Test secrets module
python3 -c "import secrets; print('OK')"

# If module missing, reinstall Python or install via package manager
```

### Issue: "Permission denied when executing script"

**Cause:** Script does not have executable permissions

**Resolution:**
```bash
chmod +x scripts/generate_secrets.sh
chmod +x scripts/setup_production.sh
```

### Issue: "Placeholders remain after secret generation"

**Cause:** sed substitution failed or unexpected file format

**Resolution:**
```bash
# Verify file format matches template
diff .env.production.template .env.production

# Check for sed errors
./scripts/generate_secrets.sh --force
```

### Issue: "Docker Compose file syntax errors"

**Cause:** Invalid YAML in docker-compose.prod.yml

**Resolution:**
```bash
# Validate YAML syntax
docker compose -f docker-compose.prod.yml config

# Fix syntax errors and retry
```

## Security Best Practices

1. **Never commit `.env.production` to version control**
   - File is in `.gitignore` by default
   - Verify with: `git status --ignored`

2. **Store secrets in encrypted vault**
   - Use 1Password, HashiCorp Vault, AWS Secrets Manager, etc.
   - Never store secrets in plaintext documentation

3. **Limit secret access to authorized personnel only**
   - Use role-based access control (RBAC)
   - Audit access logs regularly

4. **Rotate secrets on security incidents**
   - Assume compromise if any team member leaves
   - Rotate immediately after suspected breach

5. **Use different secrets per environment**
   - Development, Staging, Production must have unique keys
   - Never reuse production secrets in non-production environments

## Advanced Usage

### Custom Secret Lengths

To modify secret length, edit `generate_secrets.sh`:

```bash
# Current configuration (lines 180-185)
SECRET_KEY=$(generate_secret 32)          # 32 bytes
JWT_SECRET_KEY=$(generate_secret 32)      # 32 bytes
POSTGRES_PASSWORD=$(generate_secret 24)   # 24 bytes

# For higher entropy (e.g., 64 bytes)
SECRET_KEY=$(generate_secret 64)
```

**Note:** Longer secrets increase entropy but may impact URL length limits.

### Environment-Specific Customization

To create environment-specific setup scripts:

```bash
# Copy base script
cp scripts/setup_production.sh scripts/setup_staging.sh

# Modify environment file reference
sed -i 's/\.env\.production/\.env\.staging/g' scripts/setup_staging.sh
```

## Maintenance

### Script Updates

When updating scripts, follow version control best practices:

```bash
# Create feature branch
git checkout -b ops/update-deployment-scripts

# Make modifications
vim scripts/generate_secrets.sh

# Test locally
./scripts/setup_production.sh --skip-secrets --skip-checks

# Commit with descriptive message
git add scripts/
git commit -m "ops(scripts): enhance secret generation with additional validation"

# Submit for peer review
git push origin ops/update-deployment-scripts
```

### Testing

Before deploying script changes to production:

```bash
# Test in isolated environment (Docker container)
docker run --rm -it -v $(pwd):/workspace -w /workspace ubuntu:22.04 bash
apt update && apt install -y python3 docker.io git
./scripts/setup_production.sh
```

## Support

For issues, questions, or contributions:

- **Internal:** Contact DevOps team via internal ticketing system
- **External:** Submit issue on project repository
- **Urgent:** Contact on-call DevOps engineer

---

**Version:** 1.0.0
**Last Updated:** 2025-01-27
**Maintained By:** Privasee DevOps Team

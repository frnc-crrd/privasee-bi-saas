# Deployment Automation Implementation

## Executive Summary

Enterprise-grade production deployment automation has been implemented to ensure secure, idempotent, and auditable environment initialization. This document outlines the architecture, usage, and security guarantees of the deployment automation suite.

## Implementation Overview

### Components Delivered

| Component | Location | Purpose |
|-----------|----------|---------|
| Secret Generation Script | `scripts/generate_secrets.sh` | Cryptographically secure token generation |
| Production Setup Orchestrator | `scripts/setup_production.sh` | End-to-end environment initialization |
| Makefile | `Makefile` | Standardized command interface |
| Documentation | `scripts/README.md` | Comprehensive operational guide |
| Git Configuration | `.gitignore` | Backup directory exclusion |

### Architecture Principles

**Isolation:**
- Secrets generation logic isolated in dedicated script
- Clear separation of concerns (generation vs. orchestration)
- No coupling to application code

**Idempotency:**
- Pre-execution validation prevents accidental overwrites
- Explicit `--force` flag required for regeneration
- Timestamped backups created before any modification

**Security Context:**
- Scripts execute before container initialization
- File permissions automatically secured (600 for `.env.production`)
- Cryptographically secure random number generation (CSPRNG)

## Usage Scenarios

### Scenario 1: First-Time Production Deployment

**Context:** New production server, no existing environment configuration.

**Procedure:**

```bash
# Step 1: Clone repository
git clone <repository-url>
cd privasee-bi-saas

# Step 2: Run automated setup
make setup-prod

# Expected Output:
# - System dependencies validated
# - Production secrets generated
# - Environment configuration validated
# - Docker prerequisites verified
# - Deployment readiness summary displayed

# Step 3: Deploy application
make deploy-build

# Step 4: Verify deployment
make health
```

**Exit Conditions:**
- `.env.production` exists with all secrets populated
- File permissions set to 600
- Backup created in `.env.backups/`
- Docker containers running and healthy

---

### Scenario 2: Secret Rotation (Security Compliance)

**Context:** Periodic secret rotation (recommended every 90 days for auth keys).

**Procedure:**

```bash
# Step 1: Backup current environment
cp .env.production .env.production.pre-rotation

# Step 2: Force regenerate secrets
./scripts/generate_secrets.sh --force

# Step 3: Rebuild containers
make stop
make deploy-build

# Step 4: Verify health
make health

# Step 5: Archive old secrets to secure vault
# (Manual step - use 1Password, Vault, etc.)
```

**Impact Assessment:**
- All active user sessions invalidated (JWT tokens signed with old key)
- Database connections temporarily disrupted during restart
- Redis connections re-established with new password

**Rollback Procedure:**
If rotation causes issues, restore from backup:

```bash
# Restore previous configuration
cp .env.production.pre-rotation .env.production

# Restart containers
make stop
make deploy-build
```

---

### Scenario 3: Manual Secret Configuration

**Context:** Secrets managed externally (e.g., HashiCorp Vault, AWS Secrets Manager).

**Procedure:**

```bash
# Step 1: Create environment file from template
cp .env.production.template .env.production

# Step 2: Inject secrets from external vault
# (Example using HashiCorp Vault CLI)
vault kv get -field=secret_key secret/privasee/prod > /tmp/secret_key
sed -i "s|SECRET_KEY=.*|SECRET_KEY=$(cat /tmp/secret_key)|" .env.production
shred -u /tmp/secret_key  # Secure deletion

# Step 3: Validate environment (skip secret generation)
./scripts/setup_production.sh --skip-secrets

# Step 4: Deploy
make deploy-build
```

---

### Scenario 4: CI/CD Pipeline Integration

**Context:** Automated deployment via GitLab CI/CD, GitHub Actions, or Jenkins.

**GitLab CI/CD Example:**

```yaml
# .gitlab-ci.yml
stages:
  - test
  - deploy

test:
  stage: test
  script:
    - make quality
    - make test
  only:
    - branches

deploy:production:
  stage: deploy
  script:
    # Inject secrets from CI/CD variables
    - cp .env.production.template .env.production
    - sed -i "s|SECRET_KEY=.*|SECRET_KEY=${CI_SECRET_KEY}|" .env.production
    - sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${CI_JWT_SECRET}|" .env.production
    # ... (inject remaining secrets)

    # Validate and deploy
    - ./scripts/setup_production.sh --skip-secrets
    - docker compose -f docker-compose.prod.yml up -d --build
  only:
    - main
  when: manual
  environment:
    name: production
    url: https://app.privasee.com
```

**GitHub Actions Example:**

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  workflow_dispatch:  # Manual trigger only
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v3

      - name: Configure environment
        run: |
          cp .env.production.template .env.production
          echo "SECRET_KEY=${{ secrets.SECRET_KEY }}" >> .env.production
          echo "JWT_SECRET_KEY=${{ secrets.JWT_SECRET_KEY }}" >> .env.production
          # ... (inject remaining secrets)

      - name: Validate setup
        run: ./scripts/setup_production.sh --skip-secrets

      - name: Deploy application
        run: docker compose -f docker-compose.prod.yml up -d --build

      - name: Health check
        run: |
          sleep 10
          curl -f http://localhost:8000/health || exit 1
```

---

## Security Guarantees

### Cryptographic Security

**Random Number Generation:**
- Source: Python `secrets` module (PEP 506)
- Backend: Operating system CSPRNG (`/dev/urandom` on Linux)
- Entropy: Minimum 256 bits for authentication keys

**Token Encoding:**
- Format: URL-safe base64 (RFC 4648 Section 5)
- Character set: `A-Za-z0-9_-` (no special characters requiring escaping)
- Length: 43 characters for 32-byte tokens (32 * 4/3 ≈ 43)

### Access Control

**File Permissions:**
- `.env.production`: Mode 600 (owner read/write only)
- Scripts: Mode 755 (owner read/write/execute, others execute)
- Backups: Inherit permissions from source file

**Backup Security:**
- Location: `.env.backups/` (excluded from version control)
- Naming: Timestamped to prevent collisions
- Retention: Manual cleanup required (recommend 30-day retention)

### Audit Trail

All operations are logged to stdout/stderr with structured format:

```
[INFO] Production Secrets Generation Utility v1.0.0
[INFO] Checking dependencies...
[SUCCESS] All dependencies satisfied
[INFO] Placeholders detected. Proceeding with secret generation.
[INFO] Created backup: .env.backups/.env.production.20250127_143052.backup
[INFO] Generating cryptographically secure secrets...
[SUCCESS] Secrets generated successfully
[SUCCESS] Validation passed: All secrets generated successfully
[SUCCESS] File permissions set to 600 (owner read/write only)
```

**Log Aggregation:**
- Color codes compatible with log aggregation systems (ELK, Loki)
- ANSI escape codes can be stripped with `sed 's/\x1b\[[0-9;]*m//g'`

---

## Error Handling

### Common Errors and Resolutions

#### Error: "Secrets already exist (use --force to override)"

**Exit Code:** 2

**Cause:** `.env.production` already contains populated secrets.

**Resolution:**

```bash
# If intentional regeneration:
./scripts/generate_secrets.sh --force

# If accidental invocation:
# No action required - existing secrets are protected
```

---

#### Error: "Python secrets module is not available"

**Exit Code:** 3

**Cause:** Python installation is missing or incomplete.

**Resolution:**

```bash
# Verify Python installation
python3 --version

# Test secrets module
python3 -c "import secrets; print('OK')"

# If module missing, install Python 3.6+
sudo apt-get update
sudo apt-get install python3 python3-pip
```

---

#### Error: "Docker daemon is not running"

**Exit Code:** 2

**Cause:** Docker service is not active.

**Resolution:**

```bash
# Start Docker service
sudo systemctl start docker

# Enable auto-start on boot
sudo systemctl enable docker

# Verify status
sudo systemctl status docker
```

---

#### Error: "Validation failed: X placeholders remain"

**Exit Code:** 1

**Cause:** sed substitution failed or unexpected file format.

**Resolution:**

```bash
# Check for sed errors
./scripts/generate_secrets.sh --force 2>&1 | grep ERROR

# Verify file format
diff .env.production.template .env.production

# Manual inspection
grep "PEGAR_VALOR_GENERADO_AQUI" .env.production
```

---

## Makefile Command Reference

### Production Deployment

```bash
make setup-prod          # First-time setup (dependencies + secrets + validation)
make generate-secrets    # Generate secrets only
make deploy              # Start containers (no rebuild)
make deploy-build        # Rebuild and start containers
make stop                # Stop all containers
make restart             # Restart containers
make logs                # Follow application logs
make logs-all            # Follow all service logs
make status              # Display container status
make health              # Check health endpoints
```

### Development

```bash
make dev                 # Run development server (Flask debug mode)
make shell               # Open shell in production container
make db-shell            # Open PostgreSQL shell
```

### Code Quality

```bash
make quality             # Run all checks (linting + formatting + type checking)
make lint                # Run Ruff linter
make lint-fix            # Run Ruff linter with auto-fix
make format              # Format code with Ruff
make format-check        # Check formatting (no changes)
make typecheck           # Run Pyright type checker
```

### Testing

```bash
make test                # Run full test suite
make test-cov            # Run tests with coverage report
make test-unit           # Run unit tests only
make test-integration    # Run integration tests only
```

### Database Management

```bash
make db-migrate          # Run Alembic migrations
make db-rollback         # Rollback last migration
make db-create-migration # Create new migration (usage: make db-create-migration MSG="description")
make db-backup           # Create database backup
```

### Cleanup

```bash
make clean               # Remove temporary files and caches
make clean-docker        # Remove Docker containers, volumes, and images (DESTRUCTIVE)
```

---

## Best Practices

### 1. Never Commit Secrets

**Validation:**

```bash
# Verify .env.production is ignored
git status --ignored | grep .env.production

# Expected output:
# !! .env.production

# If not ignored, check .gitignore
grep ".env.production" .gitignore
```

### 2. Store Secrets in Encrypted Vault

**Recommended Solutions:**
- **1Password:** Team vaults with access control
- **HashiCorp Vault:** Enterprise-grade secret management
- **AWS Secrets Manager:** Cloud-native secret storage
- **Azure Key Vault:** Microsoft Azure integration

**Example: 1Password CLI**

```bash
# Store secrets in 1Password
op item create --category=login \
  --title="Privasee Production Secrets" \
  --vault="DevOps" \
  SECRET_KEY="$(grep SECRET_KEY .env.production | cut -d= -f2)" \
  JWT_SECRET_KEY="$(grep JWT_SECRET_KEY .env.production | cut -d= -f2)"
```

### 3. Rotate Secrets Regularly

**Rotation Schedule:**
- Authentication keys: Every 90 days
- Database passwords: Every 180 days
- On security incident: Immediately
- On personnel change: Within 24 hours

**Automation:**

```bash
# Add to cron for automated rotation (example: quarterly)
# /etc/cron.d/privasee-secret-rotation
0 0 1 */3 * /path/to/privasee-bi-saas/scripts/generate_secrets.sh --force && \
            /usr/bin/docker compose -f /path/to/docker-compose.prod.yml restart
```

### 4. Audit Access Logs

**Monitor for:**
- Failed authentication attempts
- Unauthorized secret access
- Unusual login patterns
- Secret rotation events

**Example: Extract security events**

```bash
# View authentication failures
docker compose -f docker-compose.prod.yml logs app | grep "Authentication failed"

# View secret rotation events
ls -lt .env.backups/ | head -10
```

### 5. Implement Least Privilege

**Access Control Matrix:**

| Role | `.env.production` Access | Script Execution | Container Access |
|------|--------------------------|------------------|------------------|
| Developer | Read-only (dev environment) | Yes (dev scripts) | No |
| DevOps Engineer | Read/Write | Yes (all scripts) | Yes (non-prod) |
| SRE | Read/Write | Yes (all scripts) | Yes (all environments) |
| Security Team | Audit logs only | No | Audit logs only |

---

## Troubleshooting

### Issue: Scripts fail with "Permission denied"

**Cause:** Scripts do not have executable permissions.

**Resolution:**

```bash
chmod +x scripts/generate_secrets.sh
chmod +x scripts/setup_production.sh
```

---

### Issue: Docker Compose file syntax errors

**Cause:** Invalid YAML in `docker-compose.prod.yml`.

**Resolution:**

```bash
# Validate syntax
docker compose -f docker-compose.prod.yml config

# Check for common issues
yamllint docker-compose.prod.yml
```

---

### Issue: Health checks fail after deployment

**Cause:** Application not ready or configuration error.

**Resolution:**

```bash
# Check container status
make status

# View application logs
make logs

# Check specific health endpoint
curl -v http://localhost:8000/health/liveness

# Inspect container
make shell
# Inside container:
cat /app/.env.production
```

---

## Maintenance

### Script Updates

When modifying scripts, follow these steps:

1. **Create feature branch:**
   ```bash
   git checkout -b ops/update-deployment-automation
   ```

2. **Make modifications:**
   ```bash
   vim scripts/generate_secrets.sh
   ```

3. **Test locally:**
   ```bash
   ./scripts/setup_production.sh --skip-secrets --skip-checks
   ```

4. **Update version number:**
   ```bash
   # In script header comments
   # Version: 1.0.0 → 1.1.0
   ```

5. **Document changes:**
   ```bash
   # Update scripts/README.md with change log
   ```

6. **Commit and push:**
   ```bash
   git add scripts/
   git commit -m "ops(scripts): enhance secret validation logic"
   git push origin ops/update-deployment-automation
   ```

7. **Create pull request:**
   - Request review from DevOps team
   - Ensure CI/CD tests pass
   - Merge to develop, then staging, then main

---

## Support

For issues or questions:

**Internal Support:**
- DevOps Team: Create ticket in internal ticketing system
- Urgent Issues: Contact on-call DevOps engineer

**External Contributors:**
- Submit issue on project repository
- Follow contribution guidelines in `CONTRIBUTING.md`

---

**Document Version:** 1.0.0
**Last Updated:** 2025-01-27
**Author:** Privasee DevOps Team
**Review Cycle:** Quarterly

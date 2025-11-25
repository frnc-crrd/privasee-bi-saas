# Deployment Guide

This guide covers deploying Privasee BI SaaS to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Application Deployment](#application-deployment)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Checklist](#security-checklist)
- [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### System Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 6+ (for caching and rate limiting)
- 2+ CPU cores
- 4GB+ RAM
- 20GB+ storage

### Required Services

- SMTP server (for email notifications)
- SQL Server (source for ETL)
- Reverse proxy (Nginx/Caddy)
- SSL certificate

## Environment Configuration

### Environment Variables

Create a `.env` file in production:

```bash
# Flask Configuration
SECRET_KEY=<generate-strong-random-key>
FLASK_ENV=production
FLASK_DEBUG=False

# Database
AUTH_DB_URI=postgresql://user:password@host:5432/privasee_users
DESTINATION__DUCKDB__CREDENTIALS=duckdb:///data/analytical_cube.duckdb

# JWT Configuration
JWT_SECRET_KEY=<generate-strong-random-key>
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/privasee/app.log

# Security
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com
HSTS_MAX_AGE=31536000
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True

# Rate Limiting
RATE_LIMIT_STORAGE_URI=redis://localhost:6379/2
RATE_LIMIT_DEFAULT=100/hour

# ETL Source
SOURCES__SQL_SERVER__CREDENTIALS=<sql-server-connection-string>

# Email (optional)
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=noreply@your-domain.com
MAIL_PASSWORD=<email-password>

# Monitoring (optional)
SENTRY_DSN=<sentry-dsn>
```

### Generate Secret Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Database Setup

### PostgreSQL Setup

1. Create database and user:

```sql
CREATE DATABASE privasee_users;
CREATE USER privasee_admin WITH ENCRYPTED PASSWORD '<secure-password>';
GRANT ALL PRIVILEGES ON DATABASE privasee_users TO privasee_admin;
```

2. Run migrations:

```bash
# Using Alembic (when migrations are created)
alembic upgrade head

# Or using Flask-Migrate
flask db upgrade
```

3. Create initial admin user:

```bash
flask shell
>>> from app.models import User
>>> from app.extensions import db, bcrypt
>>> admin = User(username='admin', email='admin@example.com', role='admin')
>>> admin.set_password('SecurePassword123!')
>>> db.session.add(admin)
>>> db.session.commit()
>>> exit()
```

### Database Backup

```bash
# Daily backup script
pg_dump -U privasee_admin privasee_users > backup_$(date +%Y%m%d).sql

# Automated backup with cron
0 2 * * * /usr/bin/pg_dump -U privasee_admin privasee_users > /backups/db_$(date +\%Y\%m\%d).sql
```

## Application Deployment

### Manual Deployment

1. Clone repository:

```bash
git clone https://github.com/your-org/privasee-bi-saas.git
cd privasee-bi-saas
```

2. Create virtual environment:

```bash
python3.11 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Configure environment:

```bash
cp .env.example .env
# Edit .env with production values
```

5. Run database migrations:

```bash
alembic upgrade head
```

6. Start application with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 --worker-class gevent --timeout 120 run:app
```

### Systemd Service

Create `/etc/systemd/system/privasee.service`:

```ini
[Unit]
Description=Privasee BI SaaS Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=privasee
Group=privasee
WorkingDirectory=/opt/privasee
Environment="PATH=/opt/privasee/venv/bin"
ExecStart=/opt/privasee/venv/bin/gunicorn \
    -w 4 \
    -b 127.0.0.1:5000 \
    --worker-class gevent \
    --timeout 120 \
    --access-logfile /var/log/privasee/access.log \
    --error-logfile /var/log/privasee/error.log \
    --log-level info \
    run:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable privasee
sudo systemctl start privasee
sudo systemctl status privasee
```

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/privasee`:

```nginx
upstream privasee_app {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Request size limits
    client_max_body_size 16M;

    # Logging
    access_log /var/log/nginx/privasee_access.log;
    error_log /var/log/nginx/privasee_error.log;

    # Application
    location / {
        proxy_pass http://privasee_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (if any)
    location /static {
        alias /opt/privasee/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health/liveness {
        proxy_pass http://privasee_app;
        access_log off;
    }
}
```

Enable site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/privasee /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    g++ \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 privasee && \
    chown -R privasee:privasee /app
USER privasee

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health/liveness || exit 1

# Start application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--worker-class", "gevent", "run:app"]
```

### Docker Compose Production

```yaml
version: '3.8'

services:
  app:
    build: .
    restart: always
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - AUTH_DB_URI=postgresql://privasee:${DB_PASSWORD}@db:5432/privasee_users
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./logs:/var/log/privasee
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health/liveness"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:14-alpine
    restart: always
    environment:
      - POSTGRES_DB=privasee_users
      - POSTGRES_USER=privasee
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U privasee"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

### Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Kubernetes Deployment

### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: privasee
```

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: privasee-config
  namespace: privasee
data:
  FLASK_ENV: "production"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
```

### Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: privasee-secrets
  namespace: privasee
type: Opaque
stringData:
  SECRET_KEY: "<your-secret-key>"
  JWT_SECRET_KEY: "<your-jwt-secret>"
  AUTH_DB_URI: "postgresql://user:pass@host:5432/db"
  REDIS_URL: "redis://redis:6379/0"
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: privasee-app
  namespace: privasee
spec:
  replicas: 3
  selector:
    matchLabels:
      app: privasee
  template:
    metadata:
      labels:
        app: privasee
    spec:
      containers:
      - name: app
        image: privasee-bi-saas:latest
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: privasee-config
        - secretRef:
            name: privasee-secrets
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: privasee-service
  namespace: privasee
spec:
  selector:
    app: privasee
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
```

### Apply Manifests

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get pods -n privasee
kubectl logs -f deployment/privasee-app -n privasee
```

## Monitoring and Logging

### Prometheus Metrics

Application exposes metrics at `/metrics` endpoint.

Configure Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'privasee'
    static_configs:
      - targets: ['app:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

Import dashboard with key metrics:

- Request rate (requests/second)
- Request latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database query time
- Cache hit rate
- Active users

### Log Aggregation

Forward logs to centralized logging:

```bash
# Filebeat configuration for ELK stack
filebeat.inputs:
- type: log
  paths:
    - /var/log/privasee/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "privasee-%{+yyyy.MM.dd}"
```

## Security Checklist

- [ ] HTTPS enforced with valid SSL certificate
- [ ] Strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Database credentials rotated regularly
- [ ] Firewall rules restrict database access
- [ ] Rate limiting enabled
- [ ] CORS configured for allowed origins only
- [ ] Security headers configured
- [ ] Regular dependency updates (Dependabot)
- [ ] Vulnerability scanning enabled
- [ ] Backup encryption enabled
- [ ] Audit logging enabled
- [ ] MFA enabled for admin accounts

## Backup and Recovery

### Database Backup

```bash
# Automated daily backups
0 2 * * * pg_dump -U privasee privasee_users | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Keep last 30 days
0 3 * * * find /backups -name "db_*.sql.gz" -mtime +30 -delete
```

### DuckDB Backup

```bash
# Backup analytical cube
cp /app/data/analytical_cube.duckdb /backups/analytical_cube_$(date +%Y%m%d).duckdb
```

### Restore Procedure

```bash
# Restore PostgreSQL
gunzip < /backups/db_20250116.sql.gz | psql -U privasee privasee_users

# Restore DuckDB
cp /backups/analytical_cube_20250116.duckdb /app/data/analytical_cube.duckdb

# Restart application
sudo systemctl restart privasee
```

## Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u privasee -n 100 -f

# Check database connection
psql -h localhost -U privasee -d privasee_users

# Check Redis connection
redis-cli ping
```

### High Memory Usage

```bash
# Check Gunicorn workers
ps aux | grep gunicorn

# Restart application
sudo systemctl restart privasee
```

### Slow Queries

```bash
# Enable PostgreSQL slow query log
ALTER DATABASE privasee_users SET log_min_duration_statement = 1000;

# Check slow queries
tail -f /var/log/postgresql/postgresql-14-main.log | grep duration
```

## Support

For production issues:

- Check logs: `/var/log/privasee/app.log`
- Health status: `https://your-domain.com/health`
- Metrics: `https://your-domain.com/metrics`
- Contact: support@your-domain.com

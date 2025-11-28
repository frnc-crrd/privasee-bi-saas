# Performance Optimization Guide

Comprehensive guide to performance optimizations implemented in the Privasee BI SaaS application.

## Overview

The application implements multiple layers of performance optimization:

1. **Response Caching** - Cache expensive analytics queries
2. **Query Optimization** - Optimize database queries with grouping and aggregation
3. **Query Monitoring** - Track and log slow database queries
4. **Connection Pooling** - Efficient database connection management
5. **Metrics Collection** - Monitor performance with Prometheus

## Response Caching

### Configuration

Caching is configured in `app/__init__.py`:

```python
# Configure caching (simple in-memory for development)
app.config["CACHE_TYPE"] = "simple"  # Change to "redis" in production
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

# Initialize cache
cache.init_app(app)
```

**Production Configuration (.env.production):**

```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:password@privasee-redis:6379/1
CACHE_DEFAULT_TIMEOUT=300
```

### Cached Endpoints

#### Analytics Endpoints

All analytics endpoints have caching enabled with query string-based cache keys:

**Sales Summary** (`/api/v1/analytics/sales/summary`)
- Cache timeout: 300 seconds (5 minutes)
- Cache key includes: start_date, end_date parameters
- Implementation:
  ```python
  @cache.cached(timeout=300, query_string=True)
  def get_sales_summary():
      # ... expensive DuckDB query
  ```

**Product Performance** (`/api/v1/analytics/sales/products`)
- Cache timeout: 300 seconds
- Cache key includes: limit, start_date, end_date parameters

**Location Performance** (`/api/v1/analytics/sales/locations`)
- Cache timeout: 300 seconds
- Cache key includes: limit, start_date, end_date parameters

**Sales Trends** (`/api/v1/analytics/sales/trends`)
- Cache timeout: 300 seconds
- Cache key includes: period, start_date, end_date parameters

**Category Breakdown** (`/api/v1/analytics/sales/categories`)
- Cache timeout: 300 seconds
- Cache key includes: category_type, start_date, end_date parameters

**Available Tables** (`/api/v1/analytics/tables`)
- Cache timeout: 600 seconds (10 minutes)
- Longer timeout since table list rarely changes

**Table Schema** (`/api/v1/analytics/tables/<table_name>/schema`)
- Cache timeout: 600 seconds
- Cache key prefix: 'table_schema'
- Longer timeout since schema rarely changes

#### Audit Log Endpoints

**Audit Statistics** (`/api/v1/audit/stats`)
- Cache timeout: 300 seconds
- Cache key includes: start_date, end_date parameters
- Optimized with GROUP BY queries (see Query Optimization section)

### Cache Key Generation

Flask-Caching automatically generates cache keys based on:

1. **Endpoint name**: Unique identifier for each route
2. **Query string**: All URL parameters (`query_string=True`)
3. **Custom key prefix**: Optional custom prefix (`key_prefix='table_schema'`)

**Example cache keys:**

```
# Sales summary with date range
flask_cache_view//api/v1/analytics/sales/summary?start_date=2024-01-01&end_date=2024-12-31

# Table schema for Productos table
flask_cache_table_schema//api/v1/analytics/tables/Productos/schema

# Audit stats without date filter
flask_cache_view//api/v1/audit/stats
```

### Cache Invalidation

#### Manual Invalidation

```python
from app.extensions import cache

# Clear specific endpoint cache
cache.delete('view//api/v1/analytics/sales/summary')

# Clear all analytics caches
cache.delete_many('view//api/v1/analytics/*')

# Clear entire cache
cache.clear()
```

#### Automatic Invalidation

Caches automatically expire after their timeout period. No manual invalidation needed for time-based expiry.

#### ETL Pipeline Invalidation

After ETL data ingestion, clear analytics caches:

```python
# In pipelines/ingest_sales_data.py (after successful ingestion)
from app import create_app
from app.extensions import cache

app = create_app()
with app.app_context():
    # Clear all analytics caches after data refresh
    cache.delete_many('view//api/v1/analytics/*')
```

### Cache Monitoring

Monitor cache performance through Prometheus metrics at `/metrics`:

```
# Cache hit rate (if using Redis)
redis_cache_hit_rate

# Cache memory usage
redis_cache_memory_usage_bytes

# Cache operations
cache_operations_total{operation="get"}
cache_operations_total{operation="set"}
cache_operations_total{operation="delete"}
```

## Query Optimization

### Audit Statistics Optimization

**Problem:** The original audit statistics endpoint executed multiple separate queries:

- 1 query per event type (potentially 10+ queries)
- 1 query per severity level (3 queries)
- 1 query for top users
- 1 query for total count

**Solution:** Optimized to use SQL GROUP BY for aggregation:

```python
# BEFORE: N queries (one per event type)
event_counts = {}
for event_type in AuditEventType:
    count = query.filter(AuditLog.event_type == event_type).count()
    if count > 0:
        event_counts[event_type.value] = count

# AFTER: Single query with GROUP BY
event_type_results = (
    db.session.query(
        AuditLog.event_type,
        func.count(AuditLog.id).label('count')
    )
    .filter(*base_query.whereclause.clauses)
    .group_by(AuditLog.event_type)
    .all()
)
event_counts = {
    event_type.value: count
    for event_type, count in event_type_results
}
```

**Performance Improvement:**
- Before: 15-20 database queries
- After: 4 database queries (75-80% reduction)
- Response time improvement: ~200ms → ~50ms

### Future Optimization Opportunities

#### Eager Loading

For endpoints with relationships, use eager loading to prevent N+1 queries:

```python
from sqlalchemy.orm import joinedload, selectinload

# Instead of lazy loading (N+1 problem)
users = User.query.all()
for user in users:
    print(user.audit_logs)  # Separate query for each user

# Use joinedload for one-to-many relationships
users = User.query.options(joinedload(User.audit_logs)).all()

# Use selectinload for better performance with large datasets
users = User.query.options(selectinload(User.audit_logs)).all()
```

#### Database Indexes

Ensure proper indexes exist for commonly filtered/sorted columns:

```python
# In models.py
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    # Create indexes for frequently queried columns
    __table_args__ = (
        db.Index('idx_audit_timestamp', 'timestamp'),
        db.Index('idx_audit_user_event', 'user_id', 'event_type'),
        db.Index('idx_audit_ip_address', 'ip_address'),
    )
```

Create migration for new indexes:

```bash
flask db revision -m "Add performance indexes to audit_logs"
```

## Query Performance Monitoring

### SQLAlchemy Event Listeners

Automatic query monitoring is implemented via SQLAlchemy event listeners in `app/core/query_monitoring.py`.

### Features

1. **Query Duration Tracking**
   - Records duration for every database query
   - Exports metrics to Prometheus
   - Categorizes by query type (SELECT, INSERT, UPDATE, DELETE)

2. **Slow Query Logging**
   - Logs queries exceeding threshold (default: 500ms)
   - Includes truncated SQL statement in logs
   - Helps identify optimization opportunities

3. **Connection Pool Monitoring**
   - Tracks active connections
   - Updates Prometheus gauge metrics
   - Helps identify connection leaks

### Configuration

Slow query threshold can be adjusted:

```python
# In app/core/query_monitoring.py
class QueryPerformanceMonitor:
    # Threshold for slow query logging (in seconds)
    SLOW_QUERY_THRESHOLD = 0.5  # Default: 500ms

    # Change to 1.0 for production (log only queries > 1 second)
    SLOW_QUERY_THRESHOLD = 1.0
```

### Monitoring Slow Queries

Check application logs for slow queries:

```bash
# Development
tail -f logs/app.log | grep "Slow query"

# Production (Docker)
docker compose -f docker-compose.prod.yml logs -f app | grep "Slow query"
```

**Example log output:**

```
2025-01-27 14:23:45 WARNING [query_monitoring] Slow query detected (0.782s): SELECT audit_logs.id, audit_logs.event_type, audit_logs.severity FROM audit_logs WHERE audit_logs.user_id = ? ORDER BY audit_logs.timestamp DESC...
```

### Prometheus Metrics

Query performance metrics available at `/metrics`:

```
# Query duration histogram (by query type)
db_query_duration_seconds_bucket{query_type="select",le="0.001"} 1234
db_query_duration_seconds_bucket{query_type="select",le="0.005"} 2345
db_query_duration_seconds_bucket{query_type="select",le="0.01"} 3456
db_query_duration_seconds_sum{query_type="select"} 45.67
db_query_duration_seconds_count{query_type="select"} 5678

# Active database connections
db_connections_active 3
```

### Query Performance Analysis

Use Prometheus queries to analyze database performance:

```promql
# Average query duration by type (last 5 minutes)
rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m])

# 95th percentile query latency
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Slow queries per minute (> 500ms)
sum(rate(db_query_duration_seconds_bucket{le="0.5"}[1m])) -
sum(rate(db_query_duration_seconds_bucket{le="0.1"}[1m]))
```

### Grafana Dashboards

Create Grafana dashboards to visualize query performance:

**Panel 1: Query Duration Over Time**
```promql
rate(db_query_duration_seconds_sum{query_type="select"}[5m]) /
rate(db_query_duration_seconds_count{query_type="select"}[5m])
```

**Panel 2: Query Throughput**
```promql
sum(rate(db_query_duration_seconds_count[5m])) by (query_type)
```

**Panel 3: Database Connections**
```promql
db_connections_active
```

## Connection Pooling

### Configuration

Connection pool settings in `app/core/config.py`:

```python
# Connection pool size (number of persistent connections)
SQLALCHEMY_POOL_SIZE: int = Field(default=10, ge=1, le=100)

# Additional connections when pool is full
SQLALCHEMY_MAX_OVERFLOW: int = Field(default=20, ge=0, le=50)

# Connection timeout (seconds)
SQLALCHEMY_POOL_TIMEOUT: int = Field(default=30, ge=5, le=60)

# Recycle connections after N seconds (prevent stale connections)
SQLALCHEMY_POOL_RECYCLE: int = Field(default=3600, ge=300, le=7200)

# Test connections before use (detect disconnects)
SQLALCHEMY_POOL_PRE_PING: bool = Field(default=True)
```

### Production Tuning

Adjust pool size based on load:

**Low Traffic** (< 100 req/min):
```bash
SQLALCHEMY_POOL_SIZE=5
SQLALCHEMY_MAX_OVERFLOW=10
```

**Medium Traffic** (100-1000 req/min):
```bash
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_MAX_OVERFLOW=20
```

**High Traffic** (> 1000 req/min):
```bash
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=30
```

### Connection Pool Monitoring

Monitor pool health:

```python
from app.extensions import db

# Get pool status
engine = db.engine
pool = engine.pool

print(f"Pool size: {pool.size()}")
print(f"Checked out connections: {pool.checkedout()}")
print(f"Overflow connections: {pool.overflow()}")
print(f"Pool status: {pool.status()}")
```

Check for connection leaks:

```bash
# If db_connections_active stays high (near pool_size + max_overflow),
# you may have connection leaks
curl http://localhost:8000/metrics | grep db_connections_active
```

## Best Practices

### 1. Cache Invalidation Strategy

**Time-Based Expiry (Current):**
- Simple and reliable
- Works well for data that updates on schedule
- Use for analytics data that refreshes hourly/daily

**Event-Based Invalidation:**
- More complex but more accurate
- Invalidate cache when data changes
- Use for real-time data requirements

```python
# Example: Invalidate cache after data update
@app.route('/api/v1/admin/refresh-data', methods=['POST'])
@require_admin()
def refresh_data():
    # Run ETL pipeline
    run_etl_pipeline()

    # Invalidate analytics caches
    cache.delete_many('view//api/v1/analytics/*')

    return success_response(message="Data refreshed and caches cleared")
```

### 2. Query Optimization Checklist

Before deploying new database queries:

- [ ] Use SELECT only needed columns (avoid SELECT *)
- [ ] Add indexes for WHERE clause columns
- [ ] Use LIMIT for paginated results
- [ ] Avoid N+1 queries (use eager loading)
- [ ] Use aggregate queries (GROUP BY) instead of loops
- [ ] Test query performance with production-like data volume
- [ ] Review query execution plan (EXPLAIN)

### 3. Monitoring and Alerting

Set up Prometheus alerts for performance issues:

```yaml
# prometheus/alerts.yml
groups:
  - name: performance
    rules:
      # Alert on slow queries
      - alert: SlowDatabaseQueries
        expr: histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries detected"
          description: "95th percentile query latency is {{ $value }}s"

      # Alert on high connection pool usage
      - alert: HighDatabaseConnections
        expr: db_connections_active > 25
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection usage"
          description: "{{ $value }} connections active (threshold: 25)"

      # Alert on low cache hit rate
      - alert: LowCacheHitRate
        expr: redis_cache_hit_rate < 0.7
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value }} (threshold: 0.7)"
```

### 4. Cache Warming

Pre-populate cache for common queries on application startup:

```python
# In app/__init__.py (after blueprint registration)
def warm_cache():
    """Pre-populate cache with common queries."""
    from app.services.analytics_service import AnalyticsService

    with app.app_context():
        analytics = AnalyticsService()

        # Warm up common queries
        analytics.get_sales_summary()  # No date filter (all-time)
        analytics.get_product_performance(limit=20)
        analytics.get_location_performance(limit=20)

        app.logger.info("Cache warmed successfully")

# Only warm cache in production (not on every restart in dev)
if settings.ENVIRONMENT == 'production' and not settings.is_testing():
    from threading import Thread
    Thread(target=warm_cache).start()
```

## Performance Testing

### Load Testing

Use Apache Bench or Locust to test performance:

**Apache Bench:**

```bash
# Test analytics endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 -H "Authorization: Bearer <token>" \
   http://localhost:8000/api/v1/analytics/sales/summary

# Expected results with caching:
# - First request: ~200ms (cache miss)
# - Subsequent requests: ~5-10ms (cache hit)
```

**Locust:**

```python
# locustfile.py
from locust import HttpUser, task, between

class AnalyticsUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login and get token
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.token = response.json()["data"]["access_token"]

    @task(3)
    def get_sales_summary(self):
        self.client.get(
            "/api/v1/analytics/sales/summary",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(2)
    def get_product_performance(self):
        self.client.get(
            "/api/v1/analytics/sales/products?limit=10",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def get_audit_stats(self):
        self.client.get(
            "/api/v1/audit/stats",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run load test:

```bash
locust -f locustfile.py --host=http://localhost:8000
# Open http://localhost:8089 to control test
```

### Database Query Analysis

Analyze slow queries in PostgreSQL:

```bash
# Enable slow query logging in PostgreSQL
docker compose -f docker-compose.prod.yml exec db psql -U privasee privasee_prod

-- Set log threshold to 500ms
ALTER DATABASE privasee_prod SET log_min_duration_statement = 500;

-- View slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## Troubleshooting

### High Cache Miss Rate

**Symptoms:**
- Slow response times despite caching
- High database load

**Diagnosis:**

```bash
# Check cache metrics
curl http://localhost:8000/metrics | grep cache

# Check cache size
docker compose exec privasee-redis redis-cli INFO memory
```

**Solutions:**

1. Increase cache timeout:
   ```python
   @cache.cached(timeout=600)  # Increase from 300 to 600
   ```

2. Switch to Redis in production:
   ```python
   app.config["CACHE_TYPE"] = "redis"
   ```

3. Ensure cache keys are consistent:
   ```python
   # Use query_string=True for parameter-based caching
   @cache.cached(timeout=300, query_string=True)
   ```

### Memory Issues with Cache

**Symptoms:**
- Redis memory usage growing
- OOM errors

**Solutions:**

1. Set Redis max memory:
   ```bash
   # In docker-compose.prod.yml
   redis:
     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

2. Reduce cache timeouts:
   ```python
   @cache.cached(timeout=180)  # Reduce from 300 to 180
   ```

3. Clear stale caches:
   ```bash
   docker compose exec privasee-redis redis-cli FLUSHDB
   ```

### Connection Pool Exhaustion

**Symptoms:**
- Timeouts waiting for database connections
- High `db_connections_active` metric

**Diagnosis:**

```python
# Check pool status
from app.extensions import db
print(db.engine.pool.status())
```

**Solutions:**

1. Increase pool size:
   ```bash
   SQLALCHEMY_POOL_SIZE=20
   SQLALCHEMY_MAX_OVERFLOW=30
   ```

2. Find connection leaks:
   ```python
   # Ensure all queries use proper session management
   try:
       result = db.session.query(User).all()
       db.session.commit()
   except Exception:
       db.session.rollback()
       raise
   ```

3. Enable connection recycling:
   ```bash
   SQLALCHEMY_POOL_RECYCLE=1800  # Recycle after 30 minutes
   ```

## References

- [Flask-Caching Documentation](https://flask-caching.readthedocs.io/)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [SQLAlchemy Event System](https://docs.sqlalchemy.org/en/20/core/event.html)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [Redis Best Practices](https://redis.io/docs/management/optimization/)

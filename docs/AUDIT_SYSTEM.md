# Audit Logging System

Comprehensive security audit trail for compliance, forensics, and threat detection.

## Overview

The audit logging system provides an immutable, append-only record of all security-relevant events in the application. It tracks authentication, authorization, account management, and data access events with full request context for forensic analysis.

### Key Features

- **Automatic Event Capture**: Authentication and authorization events logged automatically
- **Immutable Records**: Append-only audit trail prevents tampering
- **Full Request Context**: IP address, user agent, endpoint, HTTP method captured
- **Role-Based Access**: Admins see all logs, users see only their own activity
- **Flexible Queries**: Filter by user, event type, severity, date range, IP address
- **Compliance Ready**: Supports SOC 2, GDPR, HIPAA audit requirements
- **Forensic Analysis**: Detect brute force attacks, privilege escalation, data exfiltration

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Auth Routes  │  User Routes  │  Analytics Routes           │
│      │              │                  │                     │
│      └──────────────┴──────────────────┘                     │
│                     │                                        │
│              AuditService                                    │
│                     │                                        │
├─────────────────────────────────────────────────────────────┤
│                  Database Layer                              │
├─────────────────────────────────────────────────────────────┤
│  AuditLog Model  (PostgreSQL)                               │
│  - event_type, severity, user_id, username                  │
│  - ip_address, user_agent, endpoint, method                 │
│  - status_code, details (JSON), timestamp                   │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

**Table**: `audit_logs`

| Column        | Type         | Description                          | Index |
|---------------|--------------|--------------------------------------|-------|
| id            | Integer      | Primary key                          | PK    |
| event_type    | Enum         | Type of security event               | Yes   |
| severity      | Enum         | Event severity (info/warning/critical)| No    |
| user_id       | Integer      | User who triggered event (nullable)  | Yes   |
| username      | String(50)   | Username snapshot (denormalized)     | No    |
| ip_address    | String(45)   | Client IP (supports IPv6)            | Yes   |
| user_agent    | String(255)  | Client user agent                    | No    |
| endpoint      | String(255)  | API endpoint accessed                | No    |
| method        | String(10)   | HTTP method (GET, POST, etc.)        | No    |
| status_code   | Integer      | HTTP response status                 | No    |
| details       | Text         | Event metadata (JSON)                | No    |
| timestamp     | DateTime(TZ) | Event timestamp (UTC)                | Yes   |

**Indexes**:
- `event_type`: Fast queries by event type
- `user_id`: Fast queries by user
- `ip_address`: Detect attacks from specific IPs
- `timestamp`: Time-range queries for reports

## Event Types

### Authentication Events

| Event Type      | Severity | Description                     | Logged By         |
|-----------------|----------|---------------------------------|-------------------|
| LOGIN           | INFO     | Successful user authentication  | auth_routes.login |
| LOGIN_FAILED    | WARNING  | Failed authentication attempt   | auth_routes.login |
| LOGOUT          | INFO     | User session termination        | auth_routes.logout|
| PASSWORD_CHANGE | INFO     | User-initiated password update  | auth_routes.change_password |
| PASSWORD_RESET  | INFO     | Password reset via email token  | auth_routes.confirm_password_reset |

### Authorization Events

| Event Type         | Severity | Description                    | Logged By          |
|--------------------|----------|--------------------------------|--------------------|
| ROLE_CHANGE        | CRITICAL | User role modification         | user_routes.update_user |
| PERMISSION_DENIED  | WARNING  | Access attempt to forbidden resource | rbac_middleware |

### Account Management Events

| Event Type       | Severity | Description              | Logged By              |
|------------------|----------|--------------------------|------------------------|
| USER_CREATED     | INFO     | New account registration | auth_routes.register   |
| USER_DELETED     | INFO     | Account deletion         | user_routes.delete_user|
| USER_UPDATED     | INFO     | Account modification     | user_routes.update_user|
| ACCOUNT_DISABLED | CRITICAL | Account deactivation     | user_routes.update_user|
| ACCOUNT_ENABLED  | CRITICAL | Account reactivation     | user_routes.update_user|

### Data Access Events

| Event Type             | Severity | Description                 | Logged By       |
|------------------------|----------|-----------------------------|-----------------|
| DATA_EXPORT            | WARNING  | Data exported to file       | analytics_routes|
| SENSITIVE_DATA_ACCESS  | WARNING  | Access to PII/PHI data      | analytics_routes|

### System Events

| Event Type     | Severity | Description                | Logged By         |
|----------------|----------|----------------------------|-------------------|
| API_ERROR      | WARNING  | Internal server error      | error_handlers    |
| CONFIG_CHANGE  | CRITICAL | System configuration change| config_routes     |

## Usage

### Logging Events Manually

```python
from app.services.audit_service import AuditService

# Log successful login
AuditService.log_login(
    user_id=1,
    username="admin",
    status_code=200
)

# Log failed login (detects brute force)
AuditService.log_login_failed(
    username="attacker@evil.com",
    status_code=401,
    details={'reason': 'invalid_credentials', 'attempts': 5}
)

# Log role change (privilege escalation detection)
AuditService.log_role_change(
    user_id=5,
    username="analyst",
    details={'old_role': 'viewer', 'new_role': 'admin', 'changed_by': 'superadmin'},
    status_code=200
)

# Log data export (data exfiltration detection)
AuditService.log_data_export(
    user_id=3,
    username="analyst",
    details={'table': 'sales', 'rows': 50000, 'format': 'csv'},
    status_code=200
)
```

### Automatic Request Context Capture

The `AuditService` automatically captures:
- **Real Client IP**: Extracts from `X-Real-IP` or `X-Forwarded-For` headers (reverse proxy support)
- **User Agent**: Browser/client identification
- **Endpoint**: Flask route name
- **HTTP Method**: GET, POST, PUT, DELETE, etc.

No manual context passing required:

```python
# Context automatically captured from Flask request
AuditService.log_login(user_id=1, username="admin")

# Equivalent to:
AuditService.log_login(
    user_id=1,
    username="admin",
    req=request  # Automatically uses Flask's request context
)
```

### Custom Events

```python
from app.models import AuditEventType, AuditSeverity

# Log custom event
AuditService.log_event(
    event_type=AuditEventType.SENSITIVE_DATA_ACCESS,
    severity=AuditSeverity.WARNING,
    user_id=7,
    username="analyst",
    status_code=200,
    details={
        'resource': 'customer_pii',
        'fields': ['ssn', 'credit_card'],
        'record_count': 100
    }
)
```

## Querying Audit Logs

### API Endpoints

#### List Audit Logs

```bash
GET /api/v1/audit/logs?page=1&limit=20
```

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `user_id`: Filter by user ID (admin only)
- `event_type`: Filter by event type (login, logout, etc.)
- `severity`: Filter by severity (info, warning, critical)
- `start_date`: Filter events after date (ISO 8601: `2025-01-01T00:00:00Z`)
- `end_date`: Filter events before date (ISO 8601)
- `ip_address`: Filter by IP address

**Example**:

```bash
# Get all failed login attempts in last 24 hours
curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=login_failed&start_date=2025-01-26T00:00:00Z" \
  -H "Authorization: Bearer <token>"

# Get all events from specific IP (detect attacks)
curl -X GET "http://localhost:5000/api/v1/audit/logs?ip_address=192.168.1.100" \
  -H "Authorization: Bearer <admin_token>"

# Get all critical events (privilege escalations, account changes)
curl -X GET "http://localhost:5000/api/v1/audit/logs?severity=critical" \
  -H "Authorization: Bearer <admin_token>"
```

**Response**:

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": 1542,
        "event_type": "login_failed",
        "severity": "warning",
        "user_id": null,
        "username": "attacker@evil.com",
        "ip_address": "192.168.1.100",
        "user_agent": "curl/7.68.0",
        "endpoint": "auth.login",
        "method": "POST",
        "status_code": 401,
        "details": {
          "reason": "invalid_credentials",
          "attempts": 12
        },
        "timestamp": "2025-01-27T14:32:15.123456+00:00"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_items": 1,
      "total_pages": 1
    }
  },
  "message": "Retrieved 1 audit log(s)"
}
```

#### Get Single Audit Log

```bash
GET /api/v1/audit/logs/<id>
```

**Example**:

```bash
curl -X GET "http://localhost:5000/api/v1/audit/logs/1542" \
  -H "Authorization: Bearer <token>"
```

#### Get Audit Statistics (Admin Only)

```bash
GET /api/v1/audit/stats?start_date=2025-01-01T00:00:00Z
```

**Response**:

```json
{
  "success": true,
  "data": {
    "total_events": 15247,
    "events_by_type": {
      "login": 5832,
      "logout": 5104,
      "login_failed": 342,
      "password_change": 128,
      "role_change": 15
    },
    "events_by_severity": {
      "info": 14256,
      "warning": 876,
      "critical": 115
    },
    "top_users": [
      {"username": "admin", "event_count": 2341},
      {"username": "analyst1", "event_count": 1876},
      {"username": "viewer1", "event_count": 1543}
    ]
  },
  "message": "Audit statistics retrieved successfully"
}
```

## Security Considerations

### Role-Based Access Control

- **Admin Users**: Can view all audit logs across all users
- **Standard Users**: Can only view their own audit activity
- **Anonymous Users**: No access (authentication required)

### Data Retention

Audit logs are retained indefinitely by default. Implement rotation policy based on compliance requirements:

```sql
-- Example: Delete logs older than 2 years (730 days)
DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '730 days';
```

### Performance Optimization

1. **Indexes**: Critical fields (`event_type`, `user_id`, `ip_address`, `timestamp`) are indexed
2. **Pagination**: API responses limited to 100 items per page
3. **Partitioning**: For high-volume deployments, partition `audit_logs` by month

```sql
-- Example: Monthly partitioning (PostgreSQL)
CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

## Threat Detection Scenarios

### Brute Force Attack Detection

```bash
# Find IPs with >10 failed login attempts
curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=login_failed&limit=100" \
  -H "Authorization: Bearer <admin_token>" | \
  jq '.data.logs | group_by(.ip_address) | map({ip: .[0].ip_address, count: length}) | .[] | select(.count > 10)'
```

### Privilege Escalation Monitoring

```bash
# Monitor all role changes
curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=role_change" \
  -H "Authorization: Bearer <admin_token>"
```

### Data Exfiltration Detection

```bash
# Large data exports by single user
curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=data_export&user_id=5" \
  -H "Authorization: Bearer <admin_token>"
```

### Account Takeover Detection

```bash
# Logins from unusual IPs for specific user
curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=login&user_id=3" \
  -H "Authorization: Bearer <admin_token>" | \
  jq '.data.logs | map(.ip_address) | unique'
```

## Compliance Mapping

### SOC 2 Type II

- **CC6.1**: Logs all system access attempts (LOGIN, LOGIN_FAILED)
- **CC6.2**: Tracks privilege changes (ROLE_CHANGE)
- **CC6.3**: Records session termination (LOGOUT)
- **CC7.2**: Audit trail for data access (DATA_EXPORT, SENSITIVE_DATA_ACCESS)

### GDPR

- **Article 30**: Records of processing activities (USER_CREATED, DATA_EXPORT)
- **Article 32**: Security incident detection (LOGIN_FAILED, PERMISSION_DENIED)
- **Article 33**: Breach detection capabilities (anomaly analysis via /stats)

### HIPAA

- **§164.308(a)(5)(ii)(C)**: Log-in monitoring (LOGIN, LOGOUT)
- **§164.312(b)**: Audit controls (comprehensive event logging)
- **§164.308(a)(1)(ii)(D)**: Information system activity review (/stats endpoint)

## Troubleshooting

### Issue: Audit Logs Not Appearing

**Diagnosis**:

```python
from app.models import AuditLog
AuditLog.query.count()  # Should return > 0 after any auth event
```

**Resolution**:

1. Check database connection: `docker-compose logs db`
2. Verify AuditService imports: `from app.services.audit_service import AuditService`
3. Ensure database tables created: `flask db upgrade` (if using Alembic)

### Issue: Query Performance Degradation

**Diagnosis**:

```sql
-- Check index usage
EXPLAIN ANALYZE SELECT * FROM audit_logs WHERE user_id = 5;
```

**Resolution**:

1. Verify indexes exist: `\d audit_logs` (PostgreSQL)
2. Rebuild indexes: `REINDEX TABLE audit_logs;`
3. Consider partitioning for >1M records

### Issue: Permission Denied Accessing Logs

**Diagnosis**:

```bash
# Check user role in JWT
curl -X GET "http://localhost:5000/api/v1/auth/me" \
  -H "Authorization: Bearer <token>" | jq '.data.user.role'
```

**Resolution**:

- Standard users can only access their own logs
- Use admin account for cross-user queries
- Verify `user_id` filter matches authenticated user

## Migration Guide

### Existing Applications

1. **Run Database Migration**:

```bash
# Create audit_logs table
flask db upgrade
```

2. **Update Auth Routes**:

```python
from app.services.audit_service import AuditService

# Add after successful login
AuditService.log_login(user_id=user.id, username=user.username)

# Add in InvalidCredentialsError handler
AuditService.log_login_failed(username=email, details={'reason': 'invalid_credentials'})
```

3. **Test Logging**:

```bash
# Login and check audit log
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# Verify event logged
curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=login&limit=1" \
  -H "Authorization: Bearer <token>"
```

## Best Practices

1. **Always Log Sensitive Operations**: User creation, deletion, role changes, data exports
2. **Include Context**: Use `details` parameter for operation-specific metadata
3. **Monitor Critical Events**: Set up alerts for `severity=critical` events
4. **Regular Reviews**: Query `/stats` weekly for anomaly detection
5. **Immutable Logs**: Never update or delete audit records (regulatory requirement)
6. **Secure Access**: Restrict `/audit/*` endpoints to authenticated users only
7. **Archive Old Logs**: Export logs older than retention period to cold storage

## References

- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [NIST SP 800-92: Guide to Computer Security Log Management](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-92.pdf)
- [CIS Critical Security Control 8: Audit Log Management](https://www.cisecurity.org/controls/audit-log-management)

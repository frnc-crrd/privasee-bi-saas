# API Documentation

Privasee BI SaaS REST API v1

## Base URL

```
Development: http://localhost:5000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Token Lifecycle

- Access tokens expire after 1 hour
- Refresh tokens expire after 7 days
- Tokens are blacklisted upon logout

## Standard Response Format

### Success Response

```json
{
  "data": { ... },
  "message": "Operation successful",
  "status": "success"
}
```

### Error Response

```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "status": "error",
  "details": { ... }
}
```

### Paginated Response

```json
{
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  },
  "links": {
    "self": "/api/v1/users?page=1",
    "next": "/api/v1/users?page=2",
    "prev": null,
    "first": "/api/v1/users?page=1",
    "last": "/api/v1/users?page=5"
  }
}
```

## Authentication Endpoints

### Register User

Create a new user account.

**Endpoint:** `POST /auth/register`

**Request Body:**

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** `201 Created`

```json
{
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "viewer",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z"
  },
  "message": "User registered successfully"
}
```

**Validation Rules:**

- Username: 3-50 characters, alphanumeric and underscores only
- Email: Valid email format
- Password: Minimum 8 characters, must contain uppercase, lowercase, number, and special character

### Login

Authenticate and receive access/refresh tokens.

**Endpoint:** `POST /auth/login`

**Request Body:**

```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** `200 OK`

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "role": "viewer"
    }
  },
  "message": "Login successful"
}
```

**Rate Limiting:** 5 attempts per 15 minutes per IP

### Refresh Token

Get a new access token using a refresh token.

**Endpoint:** `POST /auth/refresh`

**Headers:**

```
Authorization: Bearer <refresh_token>
```

**Response:** `200 OK`

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
  },
  "message": "Token refreshed successfully"
}
```

### Logout

Invalidate current access and refresh tokens.

**Endpoint:** `POST /auth/logout`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "message": "Logged out successfully"
}
```

### Change Password

Change authenticated user's password.

**Endpoint:** `POST /auth/password/change`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "old_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response:** `200 OK`

```json
{
  "message": "Password changed successfully"
}
```

## User Management Endpoints

### Get Current User Profile

Get authenticated user's profile.

**Endpoint:** `GET /users/me`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "viewer",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "last_login": "2025-01-16T08:15:00Z"
  }
}
```

### Update Current User Profile

Update authenticated user's profile.

**Endpoint:** `PUT /users/me`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "username": "john_updated",
  "email": "john.new@example.com"
}
```

**Response:** `200 OK`

```json
{
  "data": {
    "id": 1,
    "username": "john_updated",
    "email": "john.new@example.com",
    "role": "viewer",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "last_login": "2025-01-16T08:15:00Z"
  },
  "message": "Profile updated successfully"
}
```

### List Users

List all users with pagination, filtering, sorting, and field selection.

**Endpoint:** `GET /users`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Required Role:** `analyst` or `admin`

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| page | integer | Page number (default: 1) | `?page=2` |
| per_page | integer | Items per page (default: 20, max: 100) | `?per_page=50` |
| filter[field] | string | Filter by field value | `?filter[role]=admin` |
| filter[field][operator] | string | Filter with operator | `?filter[created_at][gte]=2025-01-01` |
| search | string | Full-text search | `?search=john` |
| sort | string | Sort by field(s) | `?sort=-created_at,username` |
| fields | string | Select specific fields | `?fields=id,username,email` |

**Filter Operators:**

- `eq` - Equal to
- `ne` - Not equal to
- `gt` - Greater than
- `gte` - Greater than or equal to
- `lt` - Less than
- `lte` - Less than or equal to
- `like` - Pattern matching
- `in` - Value in list
- `is_null` - Is NULL
- `not_null` - Is not NULL

**Sort Format:**

- Prefix with `-` for descending order
- No prefix or `+` for ascending order
- Multiple fields separated by commas

**Examples:**

```
GET /api/v1/users?page=1&per_page=20&sort=-created_at
GET /api/v1/users?filter[role]=admin&filter[is_active]=true
GET /api/v1/users?filter[created_at][gte]=2025-01-01&filter[created_at][lte]=2025-01-31
GET /api/v1/users?search=john&fields=id,username,email
GET /api/v1/users?sort=-last_login,username&filter[role][in]=admin,analyst
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z",
      "last_login": "2025-01-16T08:15:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  },
  "links": {
    "self": "/api/v1/users?page=1",
    "next": "/api/v1/users?page=2",
    "prev": null,
    "first": "/api/v1/users?page=1",
    "last": "/api/v1/users?page=3"
  }
}
```

### Get User by ID

Get a specific user by ID.

**Endpoint:** `GET /users/{user_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Required Role:** `analyst` or `admin`

**Response:** `200 OK`

```json
{
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "last_login": "2025-01-16T08:15:00Z"
  }
}
```

### Update User

Update a user's information (admin only).

**Endpoint:** `PUT /users/{user_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Required Role:** `admin`

**Request Body:**

```json
{
  "username": "updated_username",
  "email": "updated@example.com",
  "role": "analyst",
  "is_active": false
}
```

**Response:** `200 OK`

```json
{
  "data": {
    "id": 1,
    "username": "updated_username",
    "email": "updated@example.com",
    "role": "analyst",
    "is_active": false,
    "created_at": "2025-01-15T10:30:00Z",
    "last_login": "2025-01-16T08:15:00Z"
  },
  "message": "User updated successfully"
}
```

### Delete User

Soft delete a user (admin only).

**Endpoint:** `DELETE /users/{user_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Required Role:** `admin`

**Response:** `200 OK`

```json
{
  "message": "User deleted successfully"
}
```

## Analytics Endpoints

### Get Sales Summary

Get aggregated sales metrics for a date range.

**Endpoint:** `GET /analytics/sales/summary`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_date | string | Yes | Start date (YYYY-MM-DD) |
| end_date | string | Yes | End date (YYYY-MM-DD) |

**Example:**

```
GET /api/v1/analytics/sales/summary?start_date=2025-01-01&end_date=2025-01-31
```

**Response:** `200 OK`

```json
{
  "data": {
    "total_sales": 125430.50,
    "order_count": 342,
    "avg_order_value": 366.78,
    "period": {
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    }
  }
}
```

### Get Sales Trends

Get time-series sales data.

**Endpoint:** `GET /analytics/sales/trends`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| period | string | Yes | Grouping period: daily, weekly, monthly |
| start_date | string | Yes | Start date (YYYY-MM-DD) |
| end_date | string | Yes | End date (YYYY-MM-DD) |

**Example:**

```
GET /api/v1/analytics/sales/trends?period=daily&start_date=2025-01-01&end_date=2025-01-31
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "date": "2025-01-01",
      "total_sales": 4532.20,
      "order_count": 15
    },
    {
      "date": "2025-01-02",
      "total_sales": 5123.45,
      "order_count": 18
    }
  ]
}
```

### Get Product Performance

Get top-performing products by sales.

**Endpoint:** `GET /analytics/products/performance`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Number of products (default: 10, max: 100) |
| start_date | string | Yes | Start date (YYYY-MM-DD) |
| end_date | string | Yes | End date (YYYY-MM-DD) |

**Example:**

```
GET /api/v1/analytics/products/performance?limit=10&start_date=2025-01-01&end_date=2025-01-31
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "product": "Laptop Pro 15",
      "sales": 45230.50,
      "quantity": 25,
      "avg_price": 1809.22
    },
    {
      "product": "Wireless Mouse",
      "sales": 2340.00,
      "quantity": 120,
      "avg_price": 19.50
    }
  ]
}
```

## Health Check Endpoints

### Overall Health

Check overall system health.

**Endpoint:** `GET /health`

**Response:** `200 OK` (healthy) or `503 Service Unavailable` (unhealthy)

```json
{
  "status": "healthy",
  "timestamp": "2025-01-16T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "application": {
      "status": "healthy",
      "message": "Application running normally",
      "uptime": "N/A"
    }
  }
}
```

### Readiness Probe

Check if application is ready to serve traffic.

**Endpoint:** `GET /health/readiness`

**Response:** `200 OK` (ready) or `503 Service Unavailable` (not ready)

```json
{
  "status": "ready",
  "timestamp": "2025-01-16T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    }
  }
}
```

### Liveness Probe

Check if application is alive.

**Endpoint:** `GET /health/liveness`

**Response:** `200 OK`

```json
{
  "status": "alive",
  "timestamp": "2025-01-16T10:30:00Z"
}
```

## Metrics Endpoint

### Prometheus Metrics

Get application metrics in Prometheus format.

**Endpoint:** `GET /metrics`

**Response:** `200 OK`

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="user_routes.list_users",status="200"} 1234.0

# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="user_routes.list_users",le="0.005"} 123.0
...
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Request successful, no content returned |
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

## Rate Limiting

Rate limits are applied per user/IP address:

- Default: 100 requests per hour
- Authentication endpoints: 5 requests per 15 minutes
- Analytics endpoints: 50 requests per hour

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642334400
```

## Request Tracking

All requests are tracked with a unique request ID. Include `X-Request-ID` header in requests for tracing:

```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

If not provided, the server generates one and includes it in the response.

## Caching

Analytics endpoints use caching to improve performance:

- Cache duration: 1 hour for analytics queries
- Cache invalidation: After ETL pipeline runs
- Cache headers: `Cache-Control`, `ETag` included in responses

## Security

### HTTPS

All production endpoints must use HTTPS. HTTP requests are redirected to HTTPS.

### CORS

Cross-Origin Resource Sharing (CORS) is configured for allowed origins only.

### Security Headers

All responses include security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: ...`

## Dashboard

Interactive Dash dashboard is available at:

```
/dashboard/
```

Requires authentication via session or JWT token.

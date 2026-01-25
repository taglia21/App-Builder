# 📖 LaunchForge API Reference

Complete API documentation for all LaunchForge modules.

---

## Table of Contents

- [Authentication](#authentication)
- [Dashboard](#dashboard)
- [Payments & Subscriptions](#payments--subscriptions)
- [Business Formation](#business-formation)
- [Monitoring & Health](#monitoring--health)
- [Deployment](#deployment)

---

## Authentication

LaunchForge uses JWT-based authentication with optional OAuth2 providers.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and get tokens |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `POST` | `/api/auth/logout` | Logout (invalidate tokens) |
| `GET` | `/api/auth/me` | Get current user info |
| `POST` | `/api/auth/password/reset` | Request password reset |
| `POST` | `/api/auth/password/change` | Change password |

### OAuth2 Providers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/auth/oauth/google` | Start Google OAuth flow |
| `GET` | `/api/auth/oauth/github` | Start GitHub OAuth flow |
| `GET` | `/api/auth/oauth/callback` | OAuth callback handler |

### Example: Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Dashboard

User dashboard for managing projects, deployments, and account settings.

### Project Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard/projects` | List all projects |
| `POST` | `/api/dashboard/projects` | Create new project |
| `GET` | `/api/dashboard/projects/{id}` | Get project details |
| `PUT` | `/api/dashboard/projects/{id}` | Update project |
| `DELETE` | `/api/dashboard/projects/{id}` | Delete project |

### Deployment Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard/deployments` | List all deployments |
| `POST` | `/api/dashboard/deployments` | Trigger new deployment |
| `GET` | `/api/dashboard/deployments/{id}` | Get deployment status |
| `DELETE` | `/api/dashboard/deployments/{id}` | Cancel deployment |

### User Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard/profile` | Get user profile |
| `PUT` | `/api/dashboard/profile` | Update profile |
| `GET` | `/api/dashboard/usage` | Get usage statistics |

### Example: List Projects

```bash
curl -X GET "http://localhost:8000/api/dashboard/projects" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

**Response:**
```json
{
  "projects": [
    {
      "id": "proj_abc123",
      "name": "My SaaS App",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "deployments": 3
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

---

## Payments & Subscriptions

Stripe-powered billing system with subscription tiers.

### Subscription Tiers

| Tier | Price | Features |
|------|-------|----------|
| **FREE** | $0/month | 1 project, 3 deployments/month, basic templates |
| **PRO** | $29/month | 10 projects, unlimited deployments, priority support |
| **ENTERPRISE** | $99/month | Unlimited projects, custom domains, white-label |

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/payments/plans` | List available plans |
| `GET` | `/api/payments/subscription` | Get current subscription |
| `POST` | `/api/payments/subscribe` | Start subscription |
| `PUT` | `/api/payments/subscription` | Change plan |
| `DELETE` | `/api/payments/subscription` | Cancel subscription |
| `GET` | `/api/payments/invoices` | List invoices |
| `GET` | `/api/payments/usage` | Get usage metrics |

### Webhooks

| Event | Description |
|-------|-------------|
| `customer.subscription.created` | New subscription started |
| `customer.subscription.updated` | Plan changed |
| `customer.subscription.deleted` | Subscription cancelled |
| `invoice.paid` | Payment successful |
| `invoice.payment_failed` | Payment failed |

### Example: Subscribe to Plan

```bash
curl -X POST "http://localhost:8000/api/payments/subscribe" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "pro_monthly",
    "payment_method_id": "pm_card_visa"
  }'
```

**Response:**
```json
{
  "subscription_id": "sub_abc123",
  "status": "active",
  "current_period_start": "2024-01-15T00:00:00Z",
  "current_period_end": "2024-02-15T00:00:00Z",
  "plan": {
    "id": "pro_monthly",
    "name": "Pro",
    "price": 2900,
    "currency": "usd"
  }
}
```

---

## Business Formation

Automated business entity creation, EIN applications, banking, and domain registration.

### LLC Formation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/business/formation` | Start LLC formation |
| `GET` | `/api/business/formation/{id}` | Get formation status |
| `GET` | `/api/business/formation/{id}/documents` | Download documents |

### EIN Application

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/business/ein` | Apply for EIN |
| `GET` | `/api/business/ein/{id}` | Get EIN status |

### Business Banking

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/business/banking` | Open business account |
| `GET` | `/api/business/banking/{id}` | Get account status |

### Domain Registration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/business/domains/search` | Search available domains |
| `POST` | `/api/business/domains` | Register domain |
| `GET` | `/api/business/domains/{id}` | Get domain status |

### Example: Start LLC Formation

```bash
curl -X POST "http://localhost:8000/api/business/formation" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Acme Startup",
    "business_type": "llc",
    "state": "DE",
    "address": {
      "street": "123 Main St",
      "city": "Wilmington",
      "state": "DE",
      "zip": "19801"
    },
    "owners": [
      {
        "name": "John Doe",
        "email": "john@example.com",
        "ownership_percentage": 100
      }
    ]
  }'
```

**Response:**
```json
{
  "formation_id": "form_xyz789",
  "status": "pending",
  "business_name": "Acme Startup",
  "state": "DE",
  "estimated_completion": "2024-01-22T00:00:00Z",
  "price": {
    "state_filing": 9000,
    "service_fee": 5000,
    "total": 14000,
    "currency": "usd"
  }
}
```

### Example: Search Domains

```bash
curl -X GET "http://localhost:8000/api/business/domains/search?query=acmestartup" \
  -H "Authorization: Bearer eyJ..."
```

**Response:**
```json
{
  "results": [
    {
      "domain": "acmestartup.com",
      "available": true,
      "price": 1299,
      "currency": "usd",
      "premium": false
    },
    {
      "domain": "acmestartup.io",
      "available": true,
      "price": 3999,
      "currency": "usd",
      "premium": false
    }
  ]
}
```

---

## Monitoring & Health

Production monitoring, health checks, metrics, and alerting.

### Health Checks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Basic health check |
| `GET` | `/health/live` | Liveness probe (K8s) |
| `GET` | `/health/ready` | Readiness probe (K8s) |
| `GET` | `/health/detailed` | Detailed component status |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/metrics` | Prometheus-format metrics |
| `GET` | `/api/metrics/summary` | JSON metrics summary |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/alerts` | List active alerts |
| `POST` | `/api/alerts/acknowledge` | Acknowledge alert |
| `GET` | `/api/alerts/history` | Alert history |

### Example: Health Check

```bash
curl -X GET "http://localhost:8000/health/detailed"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.1
    },
    "stripe": {
      "status": "healthy",
      "latency_ms": 45.3
    }
  },
  "uptime_seconds": 86400
}
```

### Example: Prometheus Metrics

```bash
curl -X GET "http://localhost:8000/metrics"
```

**Response:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/projects",status="200"} 1523
http_requests_total{method="POST",endpoint="/api/projects",status="201"} 47

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.01"} 890
http_request_duration_seconds_bucket{le="0.05"} 1456
http_request_duration_seconds_bucket{le="0.1"} 1512
```

---

## Deployment

Automated deployment to cloud providers.

### Providers

| Provider | Type | Features |
|----------|------|----------|
| **Vercel** | Frontend | Next.js, automatic SSL, global CDN |
| **Render** | Backend | Docker, PostgreSQL, Redis, auto-scaling |
| **AWS** | Enterprise | ECS, RDS, ElastiCache, S3 |

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/deploy/providers` | List available providers |
| `POST` | `/api/deploy/preview` | Create preview deployment |
| `POST` | `/api/deploy/production` | Deploy to production |
| `GET` | `/api/deploy/{id}/status` | Get deployment status |
| `GET` | `/api/deploy/{id}/logs` | Stream deployment logs |
| `DELETE` | `/api/deploy/{id}` | Rollback deployment |

### Example: Deploy to Production

```bash
curl -X POST "http://localhost:8000/api/deploy/production" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123",
    "frontend_provider": "vercel",
    "backend_provider": "render",
    "environment": "production"
  }'
```

**Response:**
```json
{
  "deployment_id": "dep_xyz789",
  "status": "building",
  "frontend": {
    "provider": "vercel",
    "status": "building",
    "url": null
  },
  "backend": {
    "provider": "render",
    "status": "building",
    "url": null
  },
  "started_at": "2024-01-15T10:30:00Z"
}
```

---

## Error Responses

All API errors follow this format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request body is invalid",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_REQUEST` | 400 | Malformed request |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limits

| Tier | Rate Limit |
|------|------------|
| FREE | 100 requests/minute |
| PRO | 1000 requests/minute |
| ENTERPRISE | 10000 requests/minute |

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1705315800
```

---

## SDKs

### Python

```python
from launchforge import LaunchForge

client = LaunchForge(api_key="sk_...")

# Create a project
project = client.projects.create(
    name="My SaaS",
    description="AI-powered task manager"
)

# Deploy
deployment = client.deploy.production(
    project_id=project.id,
    frontend="vercel",
    backend="render"
)
```

### JavaScript/TypeScript

```typescript
import { LaunchForge } from '@launchforge/sdk';

const client = new LaunchForge({ apiKey: 'sk_...' });

// Create a project
const project = await client.projects.create({
  name: 'My SaaS',
  description: 'AI-powered task manager'
});

// Deploy
const deployment = await client.deploy.production({
  projectId: project.id,
  frontend: 'vercel',
  backend: 'render'
});
```

---

## Webhooks

Configure webhooks to receive real-time notifications.

### Configuring Webhooks

```bash
curl -X POST "http://localhost:8000/api/webhooks" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhook",
    "events": [
      "project.created",
      "deployment.completed",
      "subscription.updated"
    ]
  }'
```

### Verifying Signatures

All webhook payloads include a signature header:

```
X-LaunchForge-Signature: sha256=abc123...
```

Verify using:
```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Support

- **Documentation**: https://docs.launchforge.dev
- **API Status**: https://status.launchforge.dev
- **Email**: support@launchforge.dev
- **Discord**: https://discord.gg/launchforge

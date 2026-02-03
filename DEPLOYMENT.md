# App-Builder Deployment Guide

## Prerequisites

- Python 3.10+
- Docker (optional, for containerized deployment)
- PostgreSQL database (production)
- Redis (optional, for caching)
- Stripe account (for payments)
- SendGrid/SMTP (for emails)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | `your-secret-key-here` |
| `DATABASE_URL` | Database connection string | `postgresql://user:pass@host:5432/db` |
| `STRIPE_SECRET_KEY` | Stripe API secret key | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | `whsec_...` |
| `OPENAI_API_KEY` | OpenAI API key for AI features | `sk-...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `DEBUG` | Enable debug mode | `False` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis connection (caching) | `None` |
| `SENTRY_DSN` | Sentry error tracking | `None` |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start development server
python -m src.dashboard.app
```

## Docker Deployment

### Build Image

```bash
docker build -t app-builder:latest .
```

### Run Container

```bash
docker run -d \
  --name app-builder \
  -p 8000:8000 \
  --env-file .env \
  app-builder:latest
```

### Docker Compose

```bash
docker-compose up -d
```

## Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Railway will auto-deploy on push to main

Use `.env.railway.template` as reference for required variables.

## Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure production database (PostgreSQL)
- [ ] Set strong `SECRET_KEY`
- [ ] Configure Stripe live keys
- [ ] Set up SSL/TLS
- [ ] Configure error monitoring (Sentry)
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Set up health check monitoring

## Health Check

The application exposes comprehensive health endpoints for monitoring and orchestration:

### Basic Health Check

```bash
GET /api/health
```

Returns:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-02T11:00:00.123456Z",
  "checks": {
    "llm_providers": {
      "openai": true,
      "anthropic": true
    },
    "demo_mode": false,
    "environment": "production"
  }
}
```

### Kubernetes Readiness Probe

```bash
GET /api/health/ready
```

Returns `ready` if at least one LLM provider is configured or demo mode is enabled.

```json
{
  "status": "ready",
  "checks": {
    "llm_providers": {"openai": true},
    "has_providers": true,
    "demo_mode": false
  },
  "timestamp": "2026-02-02T11:00:00.123456Z"
}
```

### Kubernetes Liveness Probe

```bash
GET /api/health/live
```

Returns `alive` if the application process is running:

```json
{
  "status": "alive",
  "timestamp": "2026-02-02T11:00:00.123456Z"
}
```

### Kubernetes Configuration

Example Kubernetes deployment with health checks:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: launchforge
spec:
  template:
    spec:
      containers:
      - name: app
        image: launchforge:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Monitoring

### Sentry Integration

Set `SENTRY_DSN` environment variable to enable error tracking.

### Prometheus Metrics

Metrics available at `/metrics` endpoint (when enabled).

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check `DATABASE_URL` format
   - Ensure database server is running
   - Verify network connectivity

2. **Stripe webhooks not working**
   - Verify `STRIPE_WEBHOOK_SECRET`
   - Check webhook endpoint URL in Stripe dashboard
   - Ensure HTTPS is configured

3. **Email not sending**
   - Verify SMTP credentials
   - Check spam folder
   - Review email service logs

## Support

For issues, please open a GitHub issue or contact support.

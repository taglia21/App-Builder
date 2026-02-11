# 🔧 Configuration Guide

## Overview

Valeric uses a combination of environment variables and a YAML configuration file for settings. This guide covers all configuration options.

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PERPLEXITY_API_KEY` | Primary LLM provider for market research | `pplx-xxxxxxxx` |

### Optional Variables

#### LLM Providers

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Fallback LLM provider | None |
| `OPENAI_API_KEY` | Alternative LLM provider | None |
| `ANTHROPIC_API_KEY` | Claude provider | None |

#### Database & Cache

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///valeric.db` |
| `REDIS_URL` | Redis connection string | None (in-memory cache) |

#### Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Auto-generated |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `7` |

#### OAuth Providers

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret |

#### Payments (Stripe)

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |

#### Deployment Providers

| Variable | Description |
|----------|-------------|
| `VERCEL_TOKEN` | Vercel deployment token |
| `RENDER_API_KEY` | Render API key |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |

#### Business Formation

| Variable | Description |
|----------|-------------|
| `STRIPE_ATLAS_API_KEY` | Stripe Atlas for LLC formation |
| `ZENBUSINESS_API_KEY` | ZenBusiness provider |
| `NAMECHEAP_API_KEY` | Domain registration |
| `NAMECHEAP_USERNAME` | Namecheap username |
| `GODADDY_API_KEY` | GoDaddy domain registration |
| `GODADDY_API_SECRET` | GoDaddy secret |
| `MERCURY_API_KEY` | Mercury banking |
| `RELAY_API_KEY` | Relay banking |

#### Monitoring

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Sentry error tracking |
| `SLACK_WEBHOOK_URL` | Slack alerts |
| `PAGERDUTY_ROUTING_KEY` | PagerDuty integration |

---

## Configuration File (config.yml)

The primary configuration file located at the project root.

### Full Example

```yaml
# Valeric Configuration
# Copy to config.yml and customize

app:
  name: "Valeric"
  version: "1.0.0"
  environment: "development"  # development, staging, production
  debug: true

# LLM Provider Settings
llm:
  default_provider: "perplexity"
  fallback_provider: "groq"
  max_tokens: 4096
  temperature: 0.7
  timeout_seconds: 30
  
  providers:
    perplexity:
      model: "sonar-pro"
      max_tokens: 4096
    groq:
      model: "llama-3.1-70b-versatile"
      max_tokens: 8192
    openai:
      model: "gpt-4"
      max_tokens: 4096

# Code Generation
code_generation:
  max_files: 100
  max_file_size_kb: 500
  output_dir: "./output"
  
  templates:
    frontend: "nextjs"  # nextjs, react, vue
    backend: "fastapi"  # fastapi, express, django
    auth: true
    database: true
    tests: true
  
  themes:
    - Modern
    - Minimalist
    - Cyberpunk
    - Corporate

# Idea Generation
idea_generation:
  num_ideas: 50
  min_score: 60
  categories:
    - SaaS
    - E-commerce
    - Marketplace
    - AI/ML
    - Fintech
    - Health
    - Education

# Intelligence Gathering
intelligence:
  sources:
    - reddit
    - hackernews
    - producthunt
    - twitter
  max_results_per_source: 20
  cache_ttl_hours: 24

# Deployment
deployment:
  default_frontend: "vercel"
  default_backend: "render"
  
  vercel:
    team_id: null  # Optional team ID
    project_settings:
      framework: "nextjs"
      build_command: "npm run build"
      output_directory: ".next"
  
  render:
    region: "oregon"
    plan: "free"  # free, starter, standard, pro

# Database
database:
  pool_size: 5
  max_overflow: 10
  echo: false

# Cache
cache:
  backend: "memory"  # memory, redis
  default_ttl: 3600

# Authentication
auth:
  algorithm: "HS256"
  access_token_expire_minutes: 60
  refresh_token_expire_days: 7
  
  oauth:
    google:
      enabled: false
    github:
      enabled: false

# Payments
payments:
  enabled: false
  provider: "stripe"
  currency: "usd"
  
  tiers:
    free:
      price: 0
      projects: 1
      deployments_per_month: 3
    pro:
      price: 2900  # cents
      price_id: "price_xxx"
      projects: 10
      deployments_per_month: -1  # unlimited
    enterprise:
      price: 9900
      price_id: "price_yyy"
      projects: -1
      deployments_per_month: -1

# Business Formation
business:
  enabled: false
  default_state: "DE"
  
  providers:
    formation: "mock"  # stripe_atlas, zenbusiness, mock
    domain: "mock"     # namecheap, godaddy, mock
    banking: "mock"    # mercury, relay, mock

# Monitoring
monitoring:
  enabled: true
  
  sentry:
    enabled: false
    traces_sample_rate: 0.1
    profiles_sample_rate: 0.1
  
  health_checks:
    enabled: true
    interval_seconds: 30
    timeout_seconds: 5
  
  metrics:
    enabled: true
    export_interval_seconds: 60
  
  alerts:
    enabled: false
    channels:
      - slack
    min_severity: "warning"  # info, warning, error, critical

# Logging
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null  # Optional log file path

# Rate Limiting
rate_limiting:
  enabled: true
  default_limit: 100
  window_seconds: 60
  
  by_tier:
    free: 100
    pro: 1000
    enterprise: 10000

# Feature Flags
features:
  interactive_build: true
  market_intelligence: true
  code_generation: true
  deployment: true
  business_formation: false
  custom_domains: false
  white_label: false
```

---

## Loading Configuration

### In Python

```python
from src.config import Settings

# Load settings
settings = Settings()

# Access values
print(settings.app_name)
print(settings.llm_provider)
print(settings.stripe_secret_key)
```

### Environment Override

Environment variables take precedence over config.yml:

```bash
# This overrides config.yml
export LLM_PROVIDER=groq
python main.py build
```

---

## Profiles

Use different configurations for different environments:

### Development

```bash
# .env.development
APP_ENV=development
DEBUG=true
DATABASE_URL=sqlite:///dev.db
```

### Production

```bash
# .env.production
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@host/db
SENTRY_DSN=https://...@sentry.io/...
```

### Loading Profiles

```bash
# Load specific profile
source .env.development
python main.py build

# Or use direnv
# .envrc
export $(cat .env.development | xargs)
```

---

## Secrets Management

### Local Development

Use `.env` files (not committed to git):

```bash
# .env (gitignored)
STRIPE_SECRET_KEY=sk_test_...
PERPLEXITY_API_KEY=pplx-...
```

### Production

Use secret managers:

**AWS Secrets Manager:**
```python
import boto3

client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='valeric/production')
```

**Docker Secrets:**
```yaml
# docker-compose.yml
secrets:
  stripe_key:
    file: ./secrets/stripe_key.txt
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: valeric-secrets
data:
  STRIPE_SECRET_KEY: base64encoded...
```

---

## Validation

Valeric validates configuration on startup:

```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    perplexity_api_key: str | None = None
    groq_api_key: str | None = None
    
    @validator('perplexity_api_key', 'groq_api_key')
    def at_least_one_llm_key(cls, v, values):
        if not v and not values.get('groq_api_key'):
            raise ValueError('At least one LLM API key required')
        return v
```

### Startup Checks

```
$ python main.py build

✓ Configuration loaded
✓ LLM provider: perplexity
✓ Database: sqlite:///valeric.db
✗ Stripe: Not configured (payments disabled)
✗ Sentry: Not configured (monitoring limited)

Starting Valeric...
```

---

## Troubleshooting

### Common Issues

**"No LLM API key found"**
```bash
# Set at least one key
export PERPLEXITY_API_KEY="pplx-..."
# OR
export GROQ_API_KEY="gsk_..."
```

**"Database connection failed"**
```bash
# Check DATABASE_URL format
export DATABASE_URL="postgresql://user:password@localhost:5432/valeric"

# For SQLite
export DATABASE_URL="sqlite:///./valeric.db"
```

**"Stripe webhook signature verification failed"**
```bash
# Ensure webhook secret matches
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

### Debug Mode

Enable verbose logging:

```bash
python main.py build -v
# OR
export LOG_LEVEL=DEBUG
python main.py build
```

---

## Reference

See also:
- [Environment Setup](../DEVELOPMENT.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [API Reference](API_REFERENCE.md)

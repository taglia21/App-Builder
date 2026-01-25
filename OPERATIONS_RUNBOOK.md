# Operations Runbook

**LaunchForge - Production Operations Guide**

*Version 1.0 | Last Updated: January 25, 2026*

## Table of Contents
1. [Service Overview](#service-overview)
2. [Infrastructure](#infrastructure)
3. [Deployment](#deployment)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Incident Response](#incident-response)
6. [Common Issues & Remediation](#common-issues--remediation)
7. [Maintenance Procedures](#maintenance-procedures)
8. [Disaster Recovery](#disaster-recovery)
9. [Security Operations](#security-operations)
10. [Contacts](#contacts)

---

## Service Overview

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                          │
│                    (Nginx/Cloudflare)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   FastAPI Application                        │
│                   (Docker Container)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Dashboard   │  │ API Routes  │  │ Background Workers  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼───┐           ┌─────▼─────┐         ┌─────▼─────┐
│ Redis │           │ PostgreSQL │         │ AI APIs   │
│ Cache │           │  Database  │         │(OpenAI/   │
│       │           │            │         │ Anthropic)│
└───────┘           └────────────┘         └───────────┘
```

### Service Endpoints
| Service | Internal Port | External Port | Health Check |
|---------|---------------|---------------|--------------|
| App | 8000 | 443 | /health |
| Dashboard | 8000 | 443 | /health |
| PostgreSQL | 5432 | - | pg_isready |
| Redis | 6379 | - | redis-cli ping |

---

## Infrastructure

### Production Environment
- **Provider**: Render / AWS
- **Region**: us-east-1 (primary), eu-west-1 (DR)
- **Container Platform**: Docker
- **Orchestration**: Docker Compose / Kubernetes

### Resource Allocation
| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| App (per instance) | 2 cores | 4GB | 10GB |
| PostgreSQL | 2 cores | 4GB | 100GB |
| Redis | 1 core | 2GB | 5GB |

### Environment Variables
```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
SECRET_KEY=<generated-secret>
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# AI Providers (at least one required)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx

# Optional
LOG_LEVEL=INFO
SENTRY_DSN=https://xxx@sentry.io/xxx
```

---

## Deployment

### Standard Deployment
```bash
# 1. Build new image
docker build -t launchforge:$(git rev-parse --short HEAD) .

# 2. Run migrations
docker-compose -f docker-compose.prod.yml run --rm app alembic upgrade head

# 3. Deploy with zero downtime
docker-compose -f docker-compose.prod.yml up -d --scale app=2 --no-recreate

# 4. Health check
curl -f https://app.launchforge.io/health

# 5. Remove old containers
docker-compose -f docker-compose.prod.yml up -d --scale app=1 --remove-orphans
```

### Rollback Procedure
```bash
# 1. Identify previous version
docker images launchforge --format "{{.Tag}}" | head -5

# 2. Rollback
docker-compose -f docker-compose.prod.yml down
docker tag launchforge:<previous-tag> launchforge:latest
docker-compose -f docker-compose.prod.yml up -d

# 3. Verify
curl -f https://app.launchforge.io/health
```

---

## Monitoring & Alerting

### Key Metrics
| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU Usage | >70% | >90% | Scale up |
| Memory Usage | >80% | >95% | Investigate leaks |
| Request Latency (p95) | >500ms | >2s | Check DB/AI APIs |
| Error Rate (5xx) | >1% | >5% | Investigate logs |
| Database Connections | >80 | >95 | Increase pool |
| Redis Memory | >70% | >90% | Eviction/scale |

### Monitoring Commands
```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100 app

# Check database connections
docker-compose -f docker-compose.prod.yml exec db psql -U launchforge -c "SELECT count(*) FROM pg_stat_activity;"

# Redis info
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO
```

---

## Incident Response

### Severity Levels
| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 | Service down | 15 min | Complete outage, data breach |
| P2 | Major degradation | 1 hour | High error rate, slow responses |
| P3 | Minor issue | 4 hours | Feature broken, minor bugs |
| P4 | Cosmetic | Next business day | UI issues, typos |

### Incident Process
1. **Detect**: Alert received or user report
2. **Acknowledge**: Respond within SLA
3. **Assess**: Determine severity and impact
4. **Communicate**: Update status page
5. **Mitigate**: Apply immediate fix
6. **Resolve**: Implement permanent fix
7. **Post-mortem**: Document within 48 hours

---

## Common Issues & Remediation

### Issue: High Memory Usage
```bash
docker stats --no-stream
docker-compose -f docker-compose.prod.yml restart app
```

### Issue: Database Connection Exhaustion
```bash
docker-compose -f docker-compose.prod.yml exec db psql -U launchforge -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '5 minutes';"
```

### Issue: Redis Memory Full
```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO memory
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB
```

---

## Maintenance Procedures

### Database Backup
```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U launchforge launchforge | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Database Restore
```bash
docker-compose -f docker-compose.prod.yml stop app
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker-compose -f docker-compose.prod.yml exec -T db psql -U launchforge launchforge
docker-compose -f docker-compose.prod.yml start app
```

---

## Disaster Recovery

### RPO/RTO Targets
| Metric | Target | Current |
|--------|--------|---------|
| RPO (Recovery Point Objective) | 1 hour | Hourly backups |
| RTO (Recovery Time Objective) | 4 hours | 2 hours tested |

---

## Security Operations

### Security Checklist
- [ ] All secrets in environment variables (not code)
- [ ] TLS 1.3 enforced
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)

### Rotating Secrets
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Contacts

### Escalation Path
1. On-call engineer (via PagerDuty)
2. Engineering manager
3. VP Engineering
4. CTO

---

## Appendix: Quick Commands

```bash
# Health check
curl -s https://app.launchforge.io/health | jq

# View recent errors
docker-compose -f docker-compose.prod.yml logs --since="1h" app | grep -i error

# Database size
docker-compose -f docker-compose.prod.yml exec db psql -U launchforge -c "SELECT pg_size_pretty(pg_database_size('launchforge'));"

# Container resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

*Document Owner: DevOps Team | Review Cycle: Quarterly*

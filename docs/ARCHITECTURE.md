# 🏗️ Valeric Architecture

## Overview

Valeric is a modular, AI-powered application builder designed for scalability, extensibility, and production readiness.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI / Web UI                            │
├─────────────────────────────────────────────────────────────────┤
│                      Application Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │  Assistant  │ │  Pipeline   │ │  Dashboard  │ │   API      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                       Service Layer                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │  Auth       │ │  Payments   │ │  Business   │ │ Deployment │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │  Database   │ │  Monitoring │ │   LLM       │ │   Cache    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. CLI Interface (`src/cli.py`)

The command-line interface provides access to all Valeric features.

**Key Commands:**
- `build` - Interactive AI assistant for building apps
- `generate` - Automated discovery pipeline
- `deploy` - Deploy to cloud providers
- `wizard` - Legacy interactive mode

### 2. Interactive Assistant (`src/assistant.py`)

The "killer feature" - a conversational AI that guides users through app creation.

**Flow:**
```
User Input → Market Research → Follow-up Questions → Profile Generation → Code Generation
```

### 3. Pipeline (`src/pipeline.py`)

Orchestrates the full startup discovery and code generation process.

**Stages:**
1. Intelligence gathering
2. Idea generation
3. Idea scoring
4. Prompt engineering
5. Code generation
6. Quality assurance
7. Deployment

---

## Module Architecture

### Authentication (`src/auth/`)

JWT-based authentication with OAuth2 support.

```
auth/
├── __init__.py      # Module exports
├── jwt.py           # Token creation/validation
├── middleware.py    # FastAPI middleware
├── oauth.py         # Google/GitHub OAuth
├── password.py      # Password hashing
├── routes.py        # API endpoints
├── schemas.py       # Pydantic models
├── service.py       # Business logic
└── tokens.py        # Token management
```

**Key Features:**
- Access/refresh token pairs
- Role-based access control (RBAC)
- Multi-provider OAuth2
- Secure password hashing (bcrypt)
- Rate limiting

### Database (`src/database/`)

SQLAlchemy-based database layer with PostgreSQL support.

```
database/
├── __init__.py      # Module exports
├── db.py            # Connection management
├── models.py        # SQLAlchemy models
└── repositories.py  # Data access layer
```

**Patterns:**
- Repository pattern for data access
- Async session management
- Migration support (Alembic)

### Payments (`src/payments/`)

Stripe-powered billing with subscription management.

```
payments/
├── __init__.py      # Module exports
├── models.py        # Pydantic models
├── stripe.py        # Stripe client wrapper
├── subscription.py  # Subscription logic
├── usage.py         # Usage tracking
└── webhooks.py      # Webhook handlers
```

**Features:**
- Three-tier pricing (FREE/PRO/ENTERPRISE)
- Usage-based metering
- Automatic invoice generation
- Webhook processing

### Dashboard (`src/dashboard/`)

HTMX-powered user interface.

```
dashboard/
├── __init__.py      # Module exports
├── app.py           # FastAPI app
├── api.py           # API endpoints
└── routes.py        # Page routes
```

**Stack:**
- FastAPI backend
- HTMX for interactivity
- Jinja2 templates
- Tailwind CSS

### Business Formation (`src/business/`)

Automated business entity creation.

```
business/
├── __init__.py      # Module exports
├── models.py        # Business models
├── formation.py     # LLC formation
├── domain.py        # Domain registration
├── banking.py       # Banking setup
└── service.py       # Orchestration
```

**Providers:**
- LLC: Stripe Atlas, ZenBusiness
- Domains: Namecheap, GoDaddy
- Banking: Mercury, Relay

### Monitoring (`src/monitoring/`)

Production observability stack.

```
monitoring/
├── __init__.py      # Module exports
├── sentry.py        # Error tracking
├── errors.py        # Error reporting
├── health.py        # Health checks
├── metrics.py       # Prometheus metrics
└── alerts.py        # Alert management
```

**Features:**
- Sentry integration
- Prometheus-compatible metrics
- Multi-channel alerting (Slack, Email, PagerDuty)
- Health check registry

### Deployment (`src/deployment/`)

Multi-cloud deployment engine.

```
deployment/
├── __init__.py
├── base.py              # Base deployer
├── models.py            # Deployment models
├── providers/
│   ├── vercel.py        # Vercel (frontend)
│   ├── render.py        # Render (backend)
│   └── detector.py      # Auto-detection
└── infrastructure/
    ├── terraform.py     # IaC generation
    └── ci_cd_generator.py
```

---

## Data Flow

### App Generation Flow

```
┌──────────┐     ┌───────────────┐     ┌──────────────┐
│  User    │────▶│  Intelligence │────▶│    Ideas     │
│  Input   │     │   Gathering   │     │  Generation  │
└──────────┘     └───────────────┘     └──────────────┘
                                              │
                                              ▼
┌──────────┐     ┌───────────────┐     ┌──────────────┐
│  Deploy  │◀────│     Code      │◀────│    Prompt    │
│          │     │   Generation  │     │  Engineering │
└──────────┘     └───────────────┘     └──────────────┘
```

### Request Flow

```
HTTP Request
     │
     ▼
┌─────────────┐
│  Middleware │ ─── Auth, Rate Limit, CORS
└─────────────┘
     │
     ▼
┌─────────────┐
│   Router    │ ─── Route matching
└─────────────┘
     │
     ▼
┌─────────────┐
│   Handler   │ ─── Business logic
└─────────────┘
     │
     ▼
┌─────────────┐
│  Database   │ ─── Data persistence
└─────────────┘
     │
     ▼
HTTP Response
```

---

## LLM Integration

### Provider Architecture

```
┌─────────────────────────────────────────┐
│            LLM Manager                  │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐       │
│  │  Perplexity │  │    Groq     │  ...  │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

**Providers:**
- **Perplexity** - Real-time market research
- **Groq** - Fast inference fallback
- **OpenAI** - General purpose
- **Mock** - Testing

**Features:**
- Automatic failover
- Response caching
- Token tracking
- Cost estimation

---

## Testing Strategy

### Test Pyramid

```
         ▲
        /│\        E2E Tests (few)
       / │ \
      /  │  \
     /───┼───\     Integration Tests
    /    │    \
   /     │     \
  /──────┼──────\  Unit Tests (many)
 /       │       \
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_generator.py        # Core generation
├── test_idea_generation.py  # Idea engine
├── test_intelligence.py     # Market research
├── test_auth.py             # Authentication
├── test_payments.py         # Stripe integration
├── test_dashboard.py        # Dashboard API
├── test_business.py         # Business formation
├── test_monitoring.py       # Monitoring stack
└── test_deployment.py       # Deployment
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/test_payments.py

# Verbose
pytest -v --tb=short
```

---

## Security

### Authentication Flow

```
┌────────┐     ┌────────┐     ┌────────┐
│ Client │────▶│  Auth  │────▶│   DB   │
└────────┘     │ Service│     └────────┘
    │          └────────┘
    │               │
    │          ┌────────┐
    │◀─────────│  JWT   │
    │          │ Tokens │
    │          └────────┘
    │
    ▼
┌────────┐
│  API   │ ─── Protected routes
└────────┘
```

### Security Measures

| Layer | Protection |
|-------|------------|
| Transport | TLS 1.3, HSTS |
| Authentication | JWT, OAuth2 |
| Authorization | RBAC, permissions |
| Data | Encryption at rest |
| API | Rate limiting, CORS |
| Monitoring | Sentry, alerts |

---

## Scalability

### Horizontal Scaling

```
                    ┌──────────────┐
                    │  Load        │
                    │  Balancer    │
                    └──────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  App 1   │    │  App 2   │    │  App 3   │
    └──────────┘    └──────────┘    └──────────┘
          │               │               │
          └───────────────┴───────────────┘
                          │
                    ┌──────────┐
                    │   Redis  │ (Session/Cache)
                    └──────────┘
                          │
                    ┌──────────┐
                    │ Postgres │ (Primary)
                    └──────────┘
```

### Performance Optimizations

- Connection pooling (SQLAlchemy)
- Redis caching
- Async I/O throughout
- CDN for static assets
- Database indexing

---

## Configuration

### Environment Variables

```bash
# Core
APP_ENV=production
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# LLM Providers
PERPLEXITY_API_KEY=pplx-...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...

# Payments
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Configuration File

```yaml
# config.yml
app:
  name: Valeric
  version: 1.0.0
  environment: production

llm:
  default_provider: perplexity
  fallback_provider: groq
  max_tokens: 4096

deployment:
  frontend: vercel
  backend: render
  
features:
  business_formation: true
  custom_domains: true
```

---

## Contributing

See [DEVELOPMENT.md](../DEVELOPMENT.md) for development setup.

### Code Style

- Python 3.12+
- Type hints required
- Pydantic for data validation
- Async/await for I/O operations
- Black for formatting
- Ruff for linting

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Write tests
4. Submit PR with description
5. Pass CI checks
6. Code review
7. Merge

---

## Multi-Agent System (Organizational Intelligence)

App-Builder implements a sophisticated multi-agent AI system based on the "Team of Rivals" architecture with three branches of governance.

### Agent Hierarchy

| Role | Responsibility | Branch |
|------|---------------|--------|
| `PLANNER` | Creates execution plans from requirements | Legislative |
| `CODE_WRITER` | Generates application code | Executive |
| `CODE_CRITIC` | Reviews code quality and correctness | Judicial |
| `OUTPUT_CRITIC` | Validates outputs match requirements | Judicial |
| `SECURITY_CRITIC` | Identifies security vulnerabilities | Judicial |
| `DEPLOYMENT_WRITER` | Creates deployment configurations | Executive |
| `DEPLOYMENT_CRITIC` | Reviews deployment safety | Judicial |
| `ORCHESTRATOR` | Coordinates all agents | Oversight |

### Three Branches of Governance

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LEGISLATIVE (Planners)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Conservative │  │  Innovative  │  │  Pragmatic   │              │
│  │   Planner    │  │   Planner    │  │   Planner    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                          │                                          │
│                    Plan Synthesis                                   │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EXECUTIVE (Writers)                              │
│              ┌──────────────────┐                                   │
│              │   Code Writer    │                                   │
│              └────────┬─────────┘                                   │
└───────────────────────┼─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    JUDICIAL (Critics)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Code Critic  │  │Security Critic│  │Output Critic│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                          │                                          │
│         ┌────────────────┴────────────────┐                        │
│    ┌────▼────┐                       ┌────▼────┐                   │
│    │ APPROVE │                       │ REJECT  │→ Back to Writers  │
│    └─────────┘                       └─────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Message Types

```python
# ExecutionPlan - Created by planners
class ExecutionPlan(BaseModel):
    plan_id: str
    app_description: str
    tech_stack: str
    acceptance_criteria: List[str]
    execution_steps: List[Dict[str, Any]]

# CriticReview - Created by critics (with veto authority)
class CriticReview(BaseModel):
    critic_role: AgentRole
    decision: CriticDecision  # APPROVE, REJECT, REQUEST_CHANGES
    reasoning: str
    issues: List[Dict[str, Any]]
    veto_reason: Optional[str]
```

### Governance Orchestrator

The `GovernanceOrchestrator` (`src/agents/governance_orchestrator.py`) coordinates all agents:

1. **Legislative Phase**: Gather plans from rival planners, synthesize into final plan
2. **Executive Phase**: Code writer generates code based on approved plan
3. **Judicial Phase**: Critics review code, approve or reject with feedback
4. **Iteration**: Rejected code returns to writers with critic feedback

This ensures high-quality output through checks and balances.

---

## References

- [API Reference](API_REFERENCE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Quick Start](../QUICK_START.md)
- [Development](../DEVELOPMENT.md)

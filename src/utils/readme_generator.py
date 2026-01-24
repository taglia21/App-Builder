"""
Enhanced README Generator

Generates comprehensive README.md files for generated apps with:
- ASCII architecture diagrams
- API documentation
- Setup instructions
- Deployment guides
- Contributing guidelines
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def generate_enhanced_readme(
    app_name: str,
    description: str,
    entity: Dict[str, Any],
    features: Dict[str, bool],
    tech_stack: Optional[Dict[str, str]] = None,
    include_architecture: bool = True,
    include_api_docs: bool = True,
    include_deployment: bool = True,
) -> str:
    """
    Generate a comprehensive README.md for a generated application.
    
    Args:
        app_name: Application name
        description: Application description
        entity: Primary entity configuration
        features: Feature flags dict
        tech_stack: Optional custom tech stack
        include_architecture: Include architecture diagram
        include_api_docs: Include detailed API docs
        include_deployment: Include deployment guide
    
    Returns:
        Complete README.md content
    """
    
    sections = []
    
    # Header
    sections.append(_generate_header(app_name, description))
    
    # Quick Start
    sections.append(_generate_quick_start(app_name, entity))
    
    # Architecture
    if include_architecture:
        sections.append(_generate_architecture(app_name, features))
    
    # Features
    sections.append(_generate_features(features))
    
    # API Documentation
    if include_api_docs:
        sections.append(_generate_api_docs(entity))
    
    # Project Structure
    sections.append(_generate_project_structure(entity))
    
    # Environment Variables
    sections.append(_generate_env_vars(features))
    
    # Local Development
    sections.append(_generate_local_dev(app_name, entity))
    
    # Deployment
    if include_deployment:
        sections.append(_generate_deployment_guide())
    
    # Tech Stack
    sections.append(_generate_tech_stack(tech_stack, features))
    
    # Testing
    sections.append(_generate_testing_guide())
    
    # Contributing
    sections.append(_generate_contributing())
    
    # Footer
    sections.append(_generate_footer())
    
    return "\n\n".join(sections)


def _generate_header(app_name: str, description: str) -> str:
    return f"""# {app_name}

{description}

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)

---"""


def _generate_quick_start(app_name: str, entity: Dict[str, Any]) -> str:
    return f"""## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (recommended)
- Or: Python 3.11+ and Node.js 20+

### Option 1: Docker (Recommended)

```bash
# Clone and start
git clone <your-repo-url>
cd {app_name.lower().replace(' ', '-')}

# Configure
cp .env.example .env

# Start everything
docker compose up --build

# 🎉 Open http://localhost:3000
```

### Option 2: Manual Setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install && npm run dev
```

### ✅ Verify Installation

| Service | URL | Expected |
|---------|-----|----------|
| Frontend | http://localhost:3000 | Login page |
| Backend | http://localhost:8000/docs | Swagger UI |
| Health | http://localhost:8000/health/ready | `{{"status": "healthy"}}` |"""


def _generate_architecture(app_name: str, features: Dict[str, bool]) -> str:
    # Build architecture diagram based on features
    has_celery = features.get('needs_background_jobs', False)
    has_ai = features.get('needs_ai_integration', False)
    
    celery_section = ""
    if has_celery:
        celery_section = """│  │                │
│  │  ┌─────────────┴─────────────┐
│  │  │      Celery Workers       │
│  │  │   (Background Tasks)      │
│  │  └───────────────────────────┘"""
    
    ai_section = ""
    if has_ai:
        ai_section = """│
│  ┌────────────────────────┐
└──│     AI/ML Services     │
   │  (OpenAI, Custom ML)   │
   └────────────────────────┘"""
    
    return f"""## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        {app_name:^25}                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │                 │         │                             │   │
│  │    Frontend     │   API   │         Backend            │   │
│  │   (Next.js)     │◀───────▶│        (FastAPI)           │   │
│  │                 │  REST   │                             │   │
│  │  Port: 3000     │         │      Port: 8000            │   │
│  │                 │         │                             │   │
│  └─────────────────┘         └──────────┬──────────────────┘   │
│                                         │                       │
│                              ┌──────────┴──────────┐           │
│                              │                     │           │
│                    ┌─────────▼───────┐  ┌─────────▼───────┐   │
│                    │                 │  │                 │   │
│                    │   PostgreSQL    │  │     Redis       │   │
│                    │   (Database)    │  │    (Cache)      │   │
│                    │                 │  │                 │   │
│                    │   Port: 5432    │  │   Port: 6379    │   │
│                    │                 │  │                 │   │
│                    └─────────────────┘  └─────────────────┘   │
{celery_section}
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
{ai_section}
```

### Data Flow

1. **User Request** → Frontend (Next.js)
2. **API Call** → Backend (FastAPI) with JWT auth
3. **Database Query** → PostgreSQL via SQLAlchemy
4. **Cache Check** → Redis for session/cache
5. **Response** → JSON back to frontend"""


def _generate_features(features: Dict[str, bool]) -> str:
    feature_list = []
    
    feature_map = {
        'needs_payments': ('💳', 'Payment Processing', 'Stripe integration for subscriptions and payments'),
        'needs_background_jobs': ('⚡', 'Background Jobs', 'Celery + Redis for async task processing'),
        'needs_ai_integration': ('🤖', 'AI Integration', 'OpenAI/LLM integration for smart features'),
        'needs_email': ('📧', 'Email System', 'Transactional emails via SMTP/SendGrid'),
    }
    
    # Always included features
    feature_list.append("- ✅ **User Authentication** - JWT-based auth with secure password hashing")
    feature_list.append("- ✅ **RESTful API** - OpenAPI/Swagger documented endpoints")
    feature_list.append("- ✅ **Database ORM** - SQLAlchemy with Alembic migrations")
    feature_list.append("- ✅ **Type Safety** - Pydantic schemas and TypeScript frontend")
    feature_list.append("- ✅ **Modern UI** - Next.js 14 with Tailwind CSS")
    
    # Conditional features
    for key, (icon, name, desc) in feature_map.items():
        if features.get(key, False):
            feature_list.append(f"- {icon} **{name}** - {desc}")
    
    return f"""## ✨ Features

{chr(10).join(feature_list)}"""


def _generate_api_docs(entity: Dict[str, Any]) -> str:
    entity_name = entity.get('name', 'Item')
    entity_lower = entity.get('lower', 'item')
    
    # Generate field documentation
    fields = entity.get('fields', [])
    field_docs = []
    for field in fields[:5]:  # Limit to 5 fields for brevity
        if isinstance(field, dict):
            name = field.get('name', 'field')
            py_type = field.get('python_type', 'str')
            required = field.get('required', True)
        elif isinstance(field, (list, tuple)):
            name = field[0] if len(field) > 0 else 'field'
            py_type = field[2] if len(field) > 2 else 'str'
            required = field[3] if len(field) > 3 else True
        else:
            continue
        
        req_str = "required" if required else "optional"
        field_docs.append(f"| `{name}` | `{py_type}` | {req_str} |")
    
    field_table = "\n".join(field_docs) if field_docs else "| `name` | `str` | required |"
    
    return f"""## 📖 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication

All protected endpoints require a Bearer token:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/users/me
```

#### Get Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{{"email": "user@example.com", "password": "password"}}'
```

### Endpoints

#### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get JWT |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Get current user |

#### {entity_name}s
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{entity_lower}s/` | List all {entity_lower}s |
| POST | `/{entity_lower}s/` | Create new {entity_lower} |
| GET | `/{entity_lower}s/{{id}}` | Get {entity_lower} by ID |
| PUT | `/{entity_lower}s/{{id}}` | Update {entity_lower} |
| DELETE | `/{entity_lower}s/{{id}}` | Delete {entity_lower} |

### {entity_name} Schema

| Field | Type | Required |
|-------|------|----------|
{field_table}
| `id` | `uuid` | auto-generated |
| `created_at` | `datetime` | auto-generated |

### Error Responses

```json
{{
  "detail": "Error message",
  "status_code": 400
}}
```

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Schema mismatch |"""


def _generate_project_structure(entity: Dict[str, Any]) -> str:
    entity_lower = entity.get('lower', 'item')
    
    return f"""## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py      # Authentication routes
│   │   │   │   └── {entity_lower}s.py  # CRUD routes
│   │   │   └── deps.py          # Dependencies
│   │   ├── core/
│   │   │   ├── config.py        # Settings
│   │   │   ├── auth.py          # JWT handling
│   │   │   └── security.py      # Password hashing
│   │   ├── crud/
│   │   │   ├── base.py          # Generic CRUD
│   │   │   └── {entity_lower}.py       # Entity CRUD
│   │   ├── db/
│   │   │   ├── base_class.py    # SQLAlchemy base
│   │   │   └── session.py       # Database session
│   │   ├── models/
│   │   │   ├── user.py          # User model
│   │   │   └── {entity_lower}.py       # Entity model
│   │   └── schemas/
│   │       ├── user.py          # User schemas
│   │       └── {entity_lower}.py       # Entity schemas
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   │   ├── (auth)/          # Auth pages
│   │   │   └── (dashboard)/     # Dashboard pages
│   │   ├── components/
│   │   │   └── ui/              # UI components
│   │   ├── config/              # Theme config
│   │   └── types/               # TypeScript types
│   ├── tailwind.config.ts
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```"""


def _generate_env_vars(features: Dict[str, bool]) -> str:
    vars_list = [
        ("DATABASE_URL", "Yes", "PostgreSQL connection string"),
        ("SECRET_KEY", "Yes", "JWT signing key (min 32 chars)"),
        ("REDIS_URL", "No", "Redis connection for caching"),
    ]
    
    if features.get('needs_email', False):
        vars_list.extend([
            ("SMTP_HOST", "No", "SMTP server host"),
            ("SMTP_PORT", "No", "SMTP server port"),
            ("SMTP_USER", "No", "SMTP username"),
            ("SMTP_PASSWORD", "No", "SMTP password"),
        ])
    
    if features.get('needs_payments', False):
        vars_list.extend([
            ("STRIPE_SECRET_KEY", "No", "Stripe secret key"),
            ("STRIPE_WEBHOOK_SECRET", "No", "Stripe webhook signing secret"),
        ])
    
    if features.get('needs_ai_integration', False):
        vars_list.extend([
            ("OPENAI_API_KEY", "No", "OpenAI API key"),
        ])
    
    rows = "\n".join([f"| `{var}` | {req} | {desc} |" for var, req, desc in vars_list])
    
    return f"""## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
{rows}

### Generating a Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```"""


def _generate_local_dev(app_name: str, entity: Dict[str, Any]) -> str:
    db_name = app_name.lower().replace(' ', '_').replace('-', '_')
    
    return f"""## 🔧 Local Development

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/{db_name}"
export SECRET_KEY="your-dev-secret-key-min-32-chars"

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set API URL
export NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm test
```"""


def _generate_deployment_guide() -> str:
    return """## 🚀 Deployment

### Docker (Recommended)

```bash
# Production build
docker compose -f docker-compose.yml up --build -d

# View logs
docker compose logs -f
```

### Deploy to Render

1. Push code to GitHub
2. Connect to [Render](https://render.com)
3. Deploy using `render.yaml` blueprint

### Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Deploy to Vercel (Frontend Only)

```bash
cd frontend
npx vercel --prod
```

### Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Use production database (not SQLite)
- [ ] Enable HTTPS
- [ ] Set CORS origins
- [ ] Configure rate limiting
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Enable backups"""


def _generate_tech_stack(custom_stack: Optional[Dict[str, str]], features: Dict[str, bool]) -> str:
    if custom_stack:
        rows = "\n".join([f"| {layer} | {tech} |" for layer, tech in custom_stack.items()])
    else:
        stack = [
            ("Frontend", "Next.js 14, React 18, TypeScript 5, Tailwind CSS"),
            ("Backend", "FastAPI 0.109, Python 3.11+, Pydantic 2.5"),
            ("Database", "PostgreSQL 15, SQLAlchemy 2.0, Alembic"),
            ("Auth", "JWT (python-jose), bcrypt"),
            ("Cache", "Redis 7"),
            ("Container", "Docker, Docker Compose"),
        ]
        
        if features.get('needs_background_jobs'):
            stack.append(("Task Queue", "Celery 5.3, Redis"))
        
        rows = "\n".join([f"| {layer} | {tech} |" for layer, tech in stack])
    
    return f"""## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
{rows}"""


def _generate_testing_guide() -> str:
    return """## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/api/test_auth.py -v
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Watch mode
npm run test:watch
```

### API Testing with cURL

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email": "test@example.com", "password": "testpass123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "test@example.com", "password": "testpass123"}'
```"""


def _generate_contributing() -> str:
    return """## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use Black for formatting
- **TypeScript**: Use ESLint and Prettier
- **Commits**: Use conventional commit messages"""


def _generate_footer() -> str:
    year = datetime.now().year
    return f"""## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Generated with ❤️ by <a href="https://github.com/startup-generator">AI Startup Generator</a>
  <br>
  © {year} All rights reserved.
</p>"""

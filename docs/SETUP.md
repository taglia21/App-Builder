# Valeric Setup Guide

This guide covers installation, configuration, and initial setup for Valeric.

## Prerequisites

- **Python 3.12+**: Required for async features and modern syntax
- **pip**: Python package manager
- **Git**: For cloning the repository
- **API Keys**: At least one LLM provider (OpenAI, Anthropic, Google, Perplexity, or Groq)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/App-Builder.git
cd App-Builder
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development with testing and linting:

```bash
pip install -r requirements-dev.txt
```

## Configuration

### Environment Variables

Valeric uses environment variables for configuration. Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Application Settings
APP_NAME=Valeric
ENVIRONMENT=development  # development, production, or testing
DEBUG=true

# LLM Provider API Keys (at least one required, or use DEMO_MODE)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
GROQ_API_KEY=gsk_...

# Optional: Database (defaults to SQLite)
DATABASE_URL=sqlite:///./valeric.db

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379

# Optional: Deployment
VERCEL_TOKEN=...
VERCEL_ORG_ID=...
VERCEL_PROJECT_ID=...

# Demo Mode (no API keys required)
DEMO_MODE=false
```

### Configuration Details

#### LLM Providers

Valeric supports multiple LLM providers. Configure at least one:

- **OpenAI**: Best for general-purpose generation
  - Get key: https://platform.openai.com/api-keys
  - Model: `gpt-4` or `gpt-3.5-turbo`

- **Anthropic**: Best for detailed analysis
  - Get key: https://console.anthropic.com/
  - Model: `claude-3-opus` or `claude-3-sonnet`

- **Google**: Good for cost-effective generation
  - Get key: https://makersuite.google.com/app/apikey
  - Model: `gemini-pro`

- **Perplexity**: Best for real-time market research
  - Get key: https://www.perplexity.ai/settings/api
  - Model: `pplx-70b-online`

- **Groq**: Fastest inference
  - Get key: https://console.groq.com/
  - Model: `mixtral-8x7b-32768`

#### Demo Mode

To try Valeric without API keys:

```bash
DEMO_MODE=true
```

Demo mode uses synthetic data and simulated responses.

#### Database

Default is SQLite (no setup required). For production:

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/valeric

# MySQL
DATABASE_URL=mysql://user:password@localhost/valeric
```

## Running the Application

### Development Server

```bash
python run_server.py
```

Or with uvicorn directly:

```bash
uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000
```

Access at: http://localhost:8000

### API Documentation

Interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health Checks

Verify the application is running:

```bash
curl http://localhost:8000/api/health
```

## Verification

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_config.py
```

### Check Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Ensure you're in the project root
cd /path/to/App-Builder

# Reinstall dependencies
pip install -r requirements.txt
```

### API Key Issues

If provider calls fail:

1. Verify API key is set: `echo $OPENAI_API_KEY`
2. Check key format (no spaces, correct prefix)
3. Verify key is valid on provider's website
4. Try demo mode: `DEMO_MODE=true`

### Port Already in Use

If port 8000 is busy:

```bash
# Use different port
uvicorn src.dashboard.app:app --port 8001
```

### Database Migration Errors

If you see database errors:

```bash
# Reset database (development only!)
rm valeric.db
python -c "from src.models import Base, engine; Base.metadata.create_all(engine)"
```

## Next Steps

- See [DEPLOYMENT.md](../DEPLOYMENT.md) for production deployment
- See [docs/ARCHITECTURE.md](ARCHITECTURE.md) for system architecture
- See [docs/API_REFERENCE.md](API_REFERENCE.md) for API details
- See [DEVELOPMENT.md](../DEVELOPMENT.md) for contributing

## Support

- **Issues**: https://github.com/yourusername/App-Builder/issues
- **Discussions**: https://github.com/yourusername/App-Builder/discussions
- **Email**: support@valeric.dev

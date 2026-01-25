# Startup Generator - Development Guide

## Architecture Overview

The system consists of 6 main engines:

### 1. Intelligence Gathering Engine (`src/intelligence/`)
- **Purpose**: Collect market data from multiple sources
- **Components**:
  - `sources/`: Individual data source integrations (Reddit, Twitter, GitHub, News, YouTube, Google)
  - `processor.py`: NLP processing for pain point extraction
  - `engine.py`: Main orchestration
- **Key Technologies**: PRAW, Tweepy, PyGithub, NewsAPI, YouTube API, Google CSE
- **Output**: IntelligenceData with pain points, emerging industries, opportunities

### 2. Idea Generation Engine (`src/idea_generation/`)
- **Purpose**: Generate startup ideas from intelligence
- **Techniques**:
  - Pain point inversion
  - Industry opportunities
  - Automation injection
  - Combination ideas
- **Output**: IdeaCatalog with 50+ StartupIdea objects

### 3. Scoring Engine (`src/scoring/`)
- **Purpose**: Evaluate and rank ideas
- **Dimensions** (9 total):
  - Market demand, Urgency, Enterprise value
  - Recurring revenue potential, Time to MVP
  - Technical complexity, Competition
  - Uniqueness, Automation potential
- **Output**: EvaluationReport with scored and ranked ideas

### 4. Prompt Engineering Engine (`src/prompt_engineering/`)
- **Purpose**: Generate comprehensive product specifications
- **Uses**: OpenAI GPT-4 or Anthropic Claude
- **Output**: ProductPrompt with detailed specifications

### 5. Refinement Engine (`src/refinement/`)
- **Purpose**: Self-critique and improve prompts
- **Checks**:
  - Consistency, Completeness
  - Architecture, Security
  - Adversarial testing
- **Process**: Iterative refinement until gold standard
- **Output**: GoldStandardPrompt with certification

### 6. Code Generation Engine (`src/code_generation/`)
- **Purpose**: Generate complete codebases
- **Generates**:
  - Backend: FastAPI with PostgreSQL, Redis
  - Frontend: Next.js with Tailwind CSS
  - Infrastructure: Docker, Terraform, GitHub Actions
  - Documentation: README, API docs, architecture
- **Output**: GeneratedCodebase with file paths and metrics

## Data Flow

```
Intelligence Sources
    ↓
IntelligenceData
    ↓
IdeaCatalog (50+ ideas)
    ↓
EvaluationReport (scored & ranked)
    ↓
Selected StartupIdea
    ↓
ProductPrompt
    ↓
GoldStandardPrompt (refined)
    ↓
GeneratedCodebase
```

## Configuration

All engines are configured via `config.yml`:

```yaml
intelligence:
  data_sources: [...]
  lookback_period: 30
  min_pain_points: 100

idea_generation:
  min_ideas: 50
  filters: {...}

scoring:
  weights: {...}
  min_total_score: 70

prompt_engineering:
  llm_provider: openai
  model: gpt-4-turbo-preview

refinement:
  max_iterations: 10
  checks: [...]

code_generation:
  backend: {framework: fastapi, ...}
  frontend: {framework: nextjs, ...}
  infrastructure: {provider: aws, ...}
```

## Adding New Data Sources

1. Create new file in `src/intelligence/sources/`
2. Inherit from `DataSource` base class
3. Implement `gather()` and `get_source_type()` methods
4. Register with `@register_source("source_name")` decorator
5. Add configuration to `config.yml`

Example:

```python
from ..base import DataSource, register_source
from ...models import SourceType

@register_source("newsource")
class NewSource(DataSource):
    def __init__(self, config):
        super().__init__(config)
        # Initialize API client
        
    def get_source_type(self) -> SourceType:
        return SourceType.NEWSOURCE
        
    async def gather(self) -> List[Dict[str, Any]]:
        # Implement gathering logic
        return data_points
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific module
pytest tests/test_intelligence.py

# Run with verbose output
pytest -v

# Run async tests
pytest tests/test_pipeline.py -v --asyncio-mode=auto

# Run email integration tests
pytest tests/test_email_integration.py -v

# Run onboarding flow tests
pytest tests/test_onboarding_flow.py -v
```

## Email Testing with Mailhog

For local development, we use Mailhog to capture and preview emails without sending them to real recipients.

### Setup

1. **Start the development stack with Mailhog:**
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

2. **Access Mailhog Web UI:**
   Open [http://localhost:8025](http://localhost:8025) in your browser.

3. **Trigger test emails:**
   - Sign up for a new account
   - Request password reset
   - Generate an app (completion email)

4. **View captured emails:**
   All emails will appear in the Mailhog web interface where you can:
   - View HTML and plain text versions
   - Check email headers
   - Test links in emails
   - Download as .eml files

### Testing with Real Resend.com

To test with the actual email service:

1. **Get a Resend API key:**
   - Sign up at [resend.com](https://resend.com)
   - Create an API key
   - Add your domain and verify DNS

2. **Configure environment:**
   ```bash
   export RESEND_API_KEY=re_your_api_key
   export FROM_EMAIL=noreply@yourdomain.com
   ```

3. **Update docker-compose.dev.yml:**
   Comment out the Mailhog SMTP settings and enable Resend.

### Email Template Development

1. **Templates location:** `src/emails/templates/`

2. **Available templates:**
   - `verification.html` - Email verification
   - `welcome.html` - Welcome email after verification
   - `password_reset.html` - Password reset link
   - `payment_confirmation.html` - Payment received
   - `app_complete.html` - App generation complete

3. **Preview templates:**
   - Admin access: Go to `/admin/email-templates`
   - Send test emails to your inbox
   - Preview in desktop and mobile views

4. **Template variables:**
   Each template receives specific variables. See `src/emails/client.py` for the convenience functions.

### Troubleshooting Email Issues

**Issue**: Emails not appearing in Mailhog
**Solution**: Ensure the app is configured to use `mailhog:1025` as SMTP host

**Issue**: Resend API errors
**Solution**: Check API key, verify domain DNS, check rate limits

**Issue**: Template rendering errors
**Solution**: Check template syntax, ensure all variables are passed

## Logging

Uses `loguru` for structured logging:

```python
from loguru import logger

logger.info("Message")
logger.warning("Warning")
logger.error("Error", exc_info=True)
```

Logs are written to:
- Console (with color)
- `./logs/execution.log` (JSON format)

## Development Workflow

1. **Setup**: Create venv, install deps
2. **Configure**: Set API keys in `.env`
3. **Test**: Run `test-intelligence` to verify API connections
4. **Develop**: Make changes to engines
5. **Test**: Run pytest
6. **Format**: Run `black src/` and `isort src/`
7. **Run**: Execute full pipeline

## Performance Optimization

- **Parallel Data Gathering**: All sources fetch concurrently
- **Caching**: Redis for API response caching
- **Batch Processing**: Process pain points in batches
- **Token Limits**: Chunk large prompts for LLM processing
- **Streaming**: Stream code generation for large files

## Error Handling

- API failures: Graceful degradation, continue with available data
- LLM failures: Fallback to template-based generation
- Validation errors: Log and skip problematic items
- Critical failures: Save intermediate results before exit

## Security Considerations

- Never commit API keys
- Use environment variables for secrets
- Validate all external data inputs
- Sanitize generated code before execution
- Review generated code for security issues

## Extending the System

### Add New Scoring Dimension

1. Add to `IdeaScores` in `models.py`
2. Add weight to config
3. Implement scoring method in `scoring/engine.py`
4. Update total score calculation

### Add New Code Generation Template

1. Add template to `code_generation/templates/`
2. Update `_generate_file()` method
3. Add to file generation workflow

### Add New Refinement Check

1. Add check name to config
2. Implement check logic in `refinement/engine.py`
3. Define pass/fail criteria

## Troubleshooting

**Issue**: API rate limits
**Solution**: Reduce `queries_per_run`, add delays, use caching

**Issue**: LLM timeouts
**Solution**: Reduce `max_tokens`, simplify prompts, add retries

**Issue**: Memory errors
**Solution**: Process in smaller batches, reduce vectorizer features

**Issue**: Missing dependencies
**Solution**: Reinstall with `pip install -r requirements.txt`

## Contributing

1. Fork repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Format code with black/isort
6. Submit pull request

## Roadmap

- [ ] Add more data sources (HackerNews, ProductHunt)
- [ ] Implement fine-tuned models for better generation
- [ ] Add market size estimation API integration
- [ ] Improve code generation with AST manipulation
- [ ] Add UI for monitoring pipeline execution
- [ ] Implement A/B testing for generated ideas
- [ ] Add deployment automation
- [ ] Create startup validation framework

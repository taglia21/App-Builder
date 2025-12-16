# 🚀 AI Startup Generator

**Generate validated startup ideas from real market data, then automatically build production-ready applications.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🎯 What It Does

```
📡 Real-Time Data    →  Scrapes GitHub, News, Search, Reddit for pain points
🔍 Pain Point Mining →  Extracts 100+ market signals automatically
💡 AI Ideation       →  Generates creative startup ideas (Groq, Gemini, GPT)
📊 Smart Scoring     →  Ranks by market demand, feasibility, TAM
💻 Code Generation   →  Outputs 37-file production apps with auth, CRUD, tests
```

**Live Demo:** Try the [Streamlit Web UI](https://your-app.streamlit.app) (coming soon)

---

## ✨ Key Features

### 🔍 Multi-Source Intelligence
- **15+ Data Sources**: GitHub trending, HackerNews, Google Trends, RSS feeds, Reddit, News APIs
- **Smart Extraction**: Identifies pain points, market trends, emerging opportunities
- **Real-Time Analysis**: Continuous monitoring of developer discussions and market signals
- **Quality Filtering**: Urgency scoring, demographic targeting, market size indicators

### 🤖 AI-Powered Ideation
- **Multiple LLM Support**: Groq (Llama 3.3), Google Gemini, OpenAI GPT, Anthropic Claude
- **Template Fallback**: Works without API keys using proven idea templates
- **Business Intelligence**: Generates revenue models, pricing strategies, TAM estimates
- **Smart Clustering**: Groups related pain points for comprehensive solutions

### 📊 Intelligent Scoring
- **Multi-Dimensional Analysis**: Market demand, technical feasibility, innovation, competition
- **Configurable Weights**: Customize scoring criteria for your focus
- **Detailed Justifications**: Understand why each idea scored the way it did
- **Market Validation**: Cross-references with real market data and trends

### 💻 Production Code Generation
- **37 Files per App**: Complete full-stack application structure
- **1,067+ Lines of Code**: Production-ready, not just scaffolding
- **Modern Stack**:
  - Backend: FastAPI + PostgreSQL + SQLAlchemy 2.0
  - Frontend: Next.js 14 + TypeScript + Tailwind CSS
  - Auth: JWT-based with refresh tokens
  - DevOps: Docker Compose + GitHub Actions CI/CD
- **Complete Features**: CRUD operations, tests, migrations, deployment configs

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- pip or poetry
- (Optional) Docker for running generated apps

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/App-Builder.git
cd App-Builder

# Install dependencies
pip install -r requirements.txt

# Optional: Install Playwright for Reddit scraping
playwright install
```

### Configuration (Optional)

Create a `.env` file for API keys (all optional - works without them):

```bash
# LLM Providers (pick one or use multiple for failover)
GROQ_API_KEY=gsk_...              # Free: 30 req/min
GEMINI_API_KEY=...                # Free: 60 req/min
OPENAI_API_KEY=...                # Paid
ANTHROPIC_API_KEY=...             # Paid

# Data Sources (optional - free sources work without keys)
REDDIT_CLIENT_ID=...              # Free Reddit API
REDDIT_CLIENT_SECRET=...
NEWSAPI_KEY=...                   # Free: 100 req/day
GOOGLE_API_KEY=...                # For Google Search
GITHUB_TOKEN=...                  # Higher GitHub rate limits
```

**Note**: System works with **zero API keys** using free sources (GitHub, HackerNews, Google Trends).

---

## 💡 Usage

### Option 1: Command Line Interface

```bash
# Run full pipeline
python main.py generate --config config.yml

# Use specific LLM provider
python main.py generate --llm-provider groq

# Demo mode (no API calls)
python main.py generate --demo

# Skip specific steps
python main.py generate --skip-refinement --skip-code-gen
```

**Output:**
```
[1/6] Gathering Intelligence... ✓ 147 pain points
[2/6] Generating Ideas...       ✓ 23 startup ideas
[3/6] Scoring Ideas...          ✓ Top: 84.5/100
[4/6] Refining Idea...          ✓ Enhanced
[5/6] Engineering Prompts...    ✓ Optimized
[6/6] Generating Code...        ✓ 37 files created

Results saved to: ./output/run_20251202_143022/
```

### Option 2: Web Interface (Streamlit)

```bash
streamlit run streamlit_app.py
```

Features:
- 🌐 Interactive dashboard
- 📊 Visual scoring charts
- 🎨 Real-time idea preview
- 📥 Export in multiple formats
- 🔍 Filter and search ideas

### Option 3: Python API

```python
import asyncio
from src.config import load_config
from src.pipeline import StartupGenerationPipeline

async def generate_startup():
    # Load configuration
    config = load_config('config.yml')
    
    # Create pipeline with Groq LLM
    pipeline = StartupGenerationPipeline(config, llm_provider='groq')
    
    # Run complete pipeline
    result = await pipeline.run(
        demo_mode=False,
        skip_refinement=False,
        skip_code_gen=False,
        output_dir='./my_startup'
    )
    
    # Access results
    print(f"Top Idea: {result.selected_idea.name}")
    print(f"Score: {result.evaluation.total_score}/100")
    print(f"Generated Code: {result.generated_code_path}")

asyncio.run(generate_startup())
```

---

## 📂 Project Structure

```
App-Builder/
├── src/
│   ├── intelligence/          # Data collection engine
│   │   ├── collectors/        # GitHub, News, Reddit scrapers
│   │   └── sources/           # Data source adapters
│   ├── idea_generation/       # AI-powered ideation
│   │   ├── engine.py          # Template-based generator
│   │   └── llm_engine.py      # AI-powered generator
│   ├── scoring/               # Multi-factor evaluation
│   ├── code_generation/       # Production code generator
│   │   ├── enhanced_engine.py # 37-file generator
│   │   └── file_templates.py  # Backend, frontend templates
│   ├── llm/                   # Multi-provider LLM client
│   ├── prompt_engineering/    # Prompt optimization
│   └── refinement/            # Idea enhancement
├── config.yml                 # Pipeline configuration
├── main.py                    # CLI entry point
├── streamlit_app.py           # Web UI
└── requirements.txt           # Python dependencies
```

---

## 🎨 Example: Generated Startup

### Input: Real GitHub Trend
```
"n8n - Fair-code workflow automation platform with native AI 
capabilities. Combine visual building with custom code, 400+ integrations."
```

### Output: Validated Idea
```yaml
Name: WorkflowAI Pro
Score: 84.5/100

Problem:
  Developers waste 15+ hours/week on repetitive API integration tasks.
  Current tools lack AI assistance and require extensive coding.

Solution:
  AI-powered workflow automation platform with visual builder,
  400+ pre-built integrations, and natural language configuration.

Market Analysis:
  TAM: $12B (workflow automation market)
  Target: 50K+ SaaS companies, DevOps teams
  Competition: Medium (n8n, Zapier, Make)
  
Revenue Model:
  Freemium SaaS
  - Free: 1K operations/month
  - Pro: $29/mo (unlimited operations)
  - Enterprise: Custom pricing + priority support

Technical Feasibility: High (8.5/10)
  Proven tech stack, clear implementation path
```

### Generated Application
```
workflow_ai_pro/
├── backend/                   # FastAPI + PostgreSQL
│   ├── app/
│   │   ├── api/endpoints/     # Auth + CRUD routes
│   │   ├── core/              # JWT, config, security
│   │   ├── crud/              # Database operations
│   │   ├── models/            # SQLAlchemy models
│   │   └── schemas/           # Pydantic validation
│   ├── tests/                 # Pytest test suite
│   ├── alembic/               # DB migrations
│   └── requirements.txt
├── frontend/                  # Next.js + TypeScript
│   ├── src/app/               # App router pages
│   ├── components/            # Reusable UI components
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml         # 3-service orchestration
├── .github/workflows/ci.yml   # CI/CD pipeline
└── README.md                  # Deployment guide
```

**Deploy immediately:**
```bash
cd workflow_ai_pro
docker-compose up -d

# Access:
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:3000
# - Database: localhost:5432
```

---

## ⚙️ Configuration

### Data Sources (`config.yml`)

```yaml
intelligence:
  data_sources:
    # FREE (no API key required) ✅
    - type: google_trends
      enabled: true
      regions: [US, GB, CA, AU]
      
    - type: hackernews
      enabled: true
      max_stories: 100
      
    - type: rss_feeds
      enabled: true
      
    # PAID/API KEY REQUIRED
    - type: reddit
      enabled: false  # Enable after adding credentials
      client_id: ${REDDIT_CLIENT_ID}
      
    - type: newsapi
      enabled: false
      api_key: ${NEWSAPI_KEY}
```

### Scoring Weights

```yaml
scoring:
  weights:
    market_demand: 0.35      # Market size & urgency
    feasibility: 0.25        # Technical difficulty
    innovation: 0.20         # Uniqueness
    competition: 0.20        # Market density
  min_total_score: 70.0      # Minimum passing score
```

### LLM Provider

```yaml
llm:
  provider: auto  # auto, groq, gemini, openai, anthropic
  model: llama-3.3-70b-versatile
  temperature: 0.7
  max_tokens: 2000
```

---

## 📊 Performance Metrics

| Metric | Value | Details |
|--------|-------|---------|
| **Data Collection** | 60s | 100-200 pain points from 5+ sources |
| **Idea Generation** | 10s | 20-50 ideas (with LLM) |
| **Code Generation** | <1s | 37 files, 1,067 lines |
| **Full Pipeline** | <90s | End-to-end execution |
| **Idea Quality** | 75-85/100 | Average score range |

### Scalability
- **Parallel Collection**: All sources run concurrently
- **LLM Failover**: Automatic fallback to backup providers
- **Rate Limiting**: Respects API quotas automatically
- **Caching**: Deduplicates pain points

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific module
pytest tests/test_idea_generation.py -v
```

---

## 📖 Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Contributing guide
- **[config.yml](config.yml)**: Complete configuration reference
- **[examples.py](examples.py)**: Python API examples

---

## 🛠️ Advanced Usage

### Custom Data Collector

```python
# src/intelligence/collectors/my_source.py
from src.models import PainPoint, SourceType

class MyCollector:
    def collect(self) -> list[PainPoint]:
        return [
            PainPoint(
                description="Users struggle with X",
                source_url="https://example.com",
                source_type=SourceType.OTHER,
                urgency_score=8.5,
                affected_demographics=["Developers"],
                market_size_indicator="Large"
            )
        ]
```

Register in `config.yml`:
```yaml
- type: my_source
  enabled: true
```

### Custom Code Templates

```python
# src/code_generation/file_templates.py
CUSTOM_ENDPOINT = """
from fastapi import APIRouter

router = APIRouter()

@router.get("/custom")
async def my_endpoint():
    return {"data": "custom response"}
"""
```

---

## 🤝 Contributing

Contributions are welcome! See [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with excellent open-source tools:
- **FastAPI** - Modern Python web framework
- **Streamlit** - Interactive data apps
- **Groq** - Fast LLM inference
- **SQLAlchemy** - Python ORM
- **Next.js** - React framework
- **Playwright** - Web automation

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/App-Builder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/App-Builder/discussions)

---

## 🎯 Roadmap

- [x] **Phase 1**: Multi-source intelligence gathering
- [x] **Phase 2**: AI-powered idea generation
- [x] **Phase 3**: Production code generation (37 files)
- [ ] **Phase 4**: Frontend enhancement (dashboards, forms)
- [ ] **Phase 5**: Advanced features (RBAC, email verification)
- [ ] **Phase 6**: Cloud deployment automation (AWS, GCP, Vercel)
- [ ] **Phase 7**: Monitoring & analytics
- [ ] **Phase 8**: Multi-language support (Node.js, Go, Rust)

---

**🚀 Transform market signals into production-ready startups in minutes!**

*Star this repo if you find it useful! ⭐*

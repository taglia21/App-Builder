# ⚡ Ignara

### AI-Powered Startup Builder

**From idea to deployed app in minutes, not months.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-4%2F4-brightgreen.svg)]()

```
 ██╗ ██████╗ ███╗   ██╗ █████╗ ██████╗  █████╗ 
 ██║██╔════╝ ████╗  ██║██╔══██╗██╔══██╗██╔══██╗
 ██║██║  ███╗██╔██╗ ██║███████║██████╔╝███████║
 ██║██║   ██║██║╚██╗██║██╔══██║██╔══██╗██╔══██║
 ██║╚██████╔╝██║ ╚████║██║  ██║██║  ██║██║  ██║
 ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
```

---

## 🎯 What is Ignara?

Ignara is a **no-code AI startup builder** that transforms your ideas into working applications. Just describe what you want to build, and let AI handle the rest.

### Core Features

| Feature | Description |
|---------|-------------|
| 🎨 **Interactive Build Mode** | Describe your idea in plain English, answer follow-up questions, get a complete app |
| 🔍 **Market Intelligence** | Real-time validation using Perplexity AI's web search |
| 💡 **Smart Generation** | AI-powered idea creation with market demand scoring |
| ⚡ **Production-Ready Code** | Full-stack applications with backend, frontend, auth, and tests |
| 🚀 **One-Click Deploy** | Deploy to Vercel (frontend), Render (backend), or your preferred cloud |

### Production Features

Ignara includes enterprise-grade infrastructure:

| Feature | Description |
|---------|-------------|
| 🏥 **Health Monitoring** | Kubernetes-ready health checks (`/api/health`, `/api/health/ready`, `/api/health/live`) |
| 📚 **API Documentation** | Auto-generated OpenAPI docs at `/docs` and `/redoc` |
| ⚙️ **Type-Safe Config** | Pydantic-based configuration with environment variables |
| 🛡️ **Error Handling** | Comprehensive exception handling with structured logging |
| 🔄 **CI/CD Pipeline** | GitHub Actions for automated testing, linting, and deployment |
| 📊 **Request Tracking** | Automatic request ID generation for debugging |

---

## 🚀 Quick Start (2 Minutes)

### 1. Install

```bash
git clone https://github.com/taglia21/App-Builder.git
cd App-Builder
pip install -r requirements.txt
```

### 2. Set API Key

```bash
# Primary: Real-time market research
# Get free key at: https://www.perplexity.ai/settings/api
export PERPLEXITY_API_KEY="pplx-..."

# Backup: Fast fallback (free tier available)
# Get free key at: https://console.groq.com/keys
export GROQ_API_KEY="gsk_..."
```

### 3. Launch the Build Assistant (The Killer Feature!)

```bash
python main.py build
```

Follow the interactive prompts:

```
💡 Step 1: Describe your startup idea
? Describe your startup idea:
  → An AI tool that helps developers write better unit tests

🔍 Step 2: Market Research (automatic with Perplexity)
✓ Found 47 relevant pain points...

💬 Step 3: Refine with follow-up questions
? Who is your target user?
? What are the 3-5 key features?
? How do you plan to monetize?

✓ Generating your complete application...

🎉 Success!
   📁 output/ai_test_generator_abc123/
   📄 156 files created
   
To run your app:
  cd output/ai_test_generator_abc123/backend
  pip install -r requirements.txt
  uvicorn main:app --reload
```

---

## 📖 Usage Modes

### Mode 1: Interactive Build (⭐ Recommended)

The killer feature. Perfect for anyone with an idea:

```bash
python main.py build
```

**What happens:**
1. Describe your startup idea in plain English
2. Ignara researches the market using real-time web intelligence
3. AI asks targeted follow-up questions (target users, features, monetization)
4. Your idea is converted into a complete startup profile
5. A production-ready full-stack app is generated
6. Option to deploy immediately

**Best for:** Entrepreneurs, indie hackers, anyone with an idea

---

### Mode 2: Automated Discovery Pipeline

Let AI discover *and* validate ideas:

```bash
# Try with demo data (no API calls needed)
python main.py generate --demo -o ./my-startup

# Run with real AI providers
python main.py generate -o ./my-startup

# Choose LLM provider
python main.py generate --llm-provider perplexity
python main.py generate --llm-provider groq
```

**What happens:**
1. Gathers real-time market intelligence (pain points, trends, competitors)
2. Generates 50+ startup ideas
3. Scores each idea on demand, feasibility, market size
4. Builds production-ready code for the top idea
5. Saves all intermediate results for review

**Best for:** Research, exploring market opportunities, benchmarking

---

### Mode 3: Build From Existing Idea

Already have a startup idea? Jump straight to code generation:

```bash
python main.py build-from-idea ideas.json -o ./my-startup
```

---

## 🛠 Commands Reference

### Core Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `build` | Interactive AI assistant (⭐ recommended!) | `python main.py build` |
| `generate` | Full pipeline (discovery → code) | `python main.py generate` |
| `build-from-idea` | Code from existing idea JSON | `python main.py build-from-idea idea.json` |
| `deploy` | Deploy generated app to cloud | `python main.py deploy ./output/app` |

### Options

```bash
# LLM Provider
--llm-provider [auto|perplexity|groq|mock]  # Default: auto

# Output & Theme
-o, --output PATH                           # Output directory
-t, --theme [Modern|Minimalist|Cyberpunk|Corporate]

# Pipeline Control
--demo                                       # Use sample data
--skip-refinement                            # Skip prompt optimization
--skip-code-gen                              # Stop after idea generation
--deploy                                     # Auto-deploy after generation

# Other
-v, --verbose                               # Detailed logging
```

### Utility Commands

```bash
python main.py demo              # See a complete example
python main.py providers         # Check LLM provider status
python main.py test-llm          # Test LLM connectivity
python main.py estimate-cost     # Estimate hosting costs
python main.py wizard            # Legacy interactive mode
```

---

## 🔍 How It Works

### The Interactive Build Flow

```
┌──────────────────────────────────────────┐
│ 1. IDEA CAPTURE                          │
│    "Describe your startup in plain text" │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│ 2. MARKET RESEARCH (via Perplexity)      │
│    • Research real pain points           │
│    • Analyze competitors                 │
│    • Validate market demand              │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│ 3. FOLLOW-UP QUESTIONS                   │
│    • Target users?                       │
│    • Key features?                       │
│    • Monetization model?                 │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│ 4. IDEA SYNTHESIS                        │
│    AI creates complete startup profile:  │
│    • Name, tagline, positioning          │
│    • Market sizing (TAM/SAM/SOM)         │
│    • Revenue model & pricing             │
│    • Competitive landscape               │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│ 5. CODE GENERATION                       │
│    Full-stack production-ready app:      │
│    ✓ Backend (FastAPI + SQLAlchemy)      │
│    ✓ Frontend (Next.js + React)          │
│    ✓ Database (PostgreSQL + migrations)  │
│    ✓ Auth (JWT + password hashing)       │
│    ✓ Docker & deployment config          │
│    ✓ API documentation (Swagger)         │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│ 6. DEPLOYMENT (Optional)                 │
│    One-click deploy to cloud:            │
│    • Frontend → Vercel                   │
│    • Backend → Render or Railway         │
└──────────────────────────────────────────┘
```

### The Automated Discovery Pipeline

```
Market Intelligence → Idea Generation → Scoring → Prompt Engineering 
    → Refinement → Code Generation → Quality Assurance → Output
```

1. **Intelligence Gathering**: Scrapes Reddit, GitHub, Twitter, news for pain points
2. **Idea Generation**: Creates 50+ startup ideas from top pain points
3. **Scoring**: Evaluates ideas on market demand, feasibility, TAM/SAM/SOM
4. **Prompt Engineering**: Converts top idea into detailed product spec
5. **Refinement**: Optimizes spec to "gold standard" quality
6. **Code Generation**: Creates production-ready full-stack app
7. **QA**: Validates generated code for best practices
8. **Output**: Ready-to-run and deploy application

---

## 📊 What Gets Generated

### Backend (FastAPI)

```
backend/
├── main.py                 # FastAPI app with routes
├── models.py              # SQLAlchemy ORM models  
├── schemas.py             # Pydantic request/response schemas
├── database.py            # Database configuration
├── auth.py                # JWT authentication
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container image
└── docker-compose.yml     # Local development setup
```

### Frontend (Next.js)

```
frontend/
├── app/                   # Next.js app directory
├── components/            # React components (built for your theme)
├── hooks/                 # Custom React hooks
├── public/                # Static assets
├── package.json           # Node dependencies
├── Dockerfile             # Production container
└── .env.example           # Configuration template
```

### Documentation

```
docs/
├── API.md                 # REST API documentation
├── ARCHITECTURE.md        # System design overview
├── DEPLOYMENT.md          # Cloud deployment guide
└── DEVELOPMENT.md         # Setup for local development
```

---

## 🤖 AI Providers

### Perplexity (⭐ Recommended)

- **Real-time web search** built into responses
- Perfect for market research and idea validation
- Models: `sonar-pro` (default), `sonar-deep-research`, `sonar-reasoning`
- Cost: $5/month for 300 daily questions (generous free tier)
- Get key: https://www.perplexity.ai/settings/api

```bash
export PERPLEXITY_API_KEY="pplx-..."
python main.py generate --llm-provider perplexity
```

### Groq (Fast Fallback)

- Ultra-fast inference
- Free tier: 3 requests/minute
- Fallback when Perplexity is unavailable
- Get key: https://console.groq.com/keys

```bash
export GROQ_API_KEY="gsk_..."
python main.py generate --llm-provider groq
```

### Mock Mode (Testing)

- No API calls needed
- Perfect for development and testing
- Uses predefined responses

```bash
python main.py generate --llm-provider mock --demo
```

### Auto Mode (Recommended)

Automatically selects the best available provider:

```bash
python main.py generate --llm-provider auto
```

**Priority:** Perplexity → Groq → Mock

---

## 🎨 UI Themes

Generated apps come in 4 professional themes:

- **Modern**: Clean, contemporary design (default)
- **Minimalist**: Elegant, distraction-free
- **Cyberpunk**: Bold, futuristic aesthetic
- **Corporate**: Professional, enterprise-ready

```bash
python main.py build --theme Cyberpunk
```

---

## 🚀 Deployment

### Deploy to Cloud (One Command)

```bash
python main.py deploy ./output/my-startup
```

**Deploys to:**
- **Frontend**: Vercel (automatic)
- **Backend**: Render (automatic)

**Prerequisites:**
- Vercel account (free)
- Render account (free tier available)

### Manual Deployment

Each generated app includes Docker:

```bash
cd ./output/my-startup

# Build Docker images
docker-compose build

# Run locally
docker-compose up

# Deploy to Docker registry
docker push registry.example.com/my-startup:latest
```

---

## 📈 Project Structure

```
Ignara/
├── src/
│   ├── assistant.py           # Interactive build mode ✨
│   ├── cli.py                 # Command-line interface
│   ├── pipeline.py            # Main orchestration
│   ├── models.py              # Data models
│   ├── llm/                   # LLM providers (Perplexity, Groq)
│   ├── code_generation/       # Code gen engine
│   ├── intelligence/          # Market research
│   ├── idea_generation/       # Idea creation
│   ├── prompt_engineering/    # Spec generation
│   ├── refinement/            # Prompt optimization
│   ├── scoring/               # Idea evaluation
│   ├── deployment/            # Cloud deployment
│   └── utils/                 # Helpers
├── tests/                     # Unit & integration tests
├── config.yml                 # Configuration template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 💡 Examples

### Example 1: Build an AI Test Generator

```bash
$ python main.py build
? Describe your startup idea:
  An AI tool that analyzes code and generates comprehensive unit tests 
  using advanced static analysis and machine learning.

[Ignara researches...]

? Who is your target user?
  Junior developers and small teams
  
? What are the 3-5 key features?
  Automatic test generation, Code analysis, Coverage reports, IDE integration

? How do you plan to monetize?
  Subscription

Generated: AI Test Generator
Output: output/ai_test_generator_a1b2c3d4/
```

### Example 2: Market Research

```bash
$ python main.py generate -o ./research

[Step 1/6] Gathering Intelligence
  ✓ Found 127 pain points
  ✓ Analyzed 45 competitors
  ✓ Identified 8 emerging industries

[Step 2/6] Generating Ideas
  ✓ Created 52 startup ideas
  
[Step 3/6] Scoring Ideas
  ✓ Top idea: "AI Code Review Assistant" (Score: 87.3/100)
  
[Step 4-6] Generating Code...
  ✓ Built complete full-stack application

$ cd research/backend && pip install -r requirements.txt
$ uvicorn main:app --reload
```

---

## 🧪 Testing

Run the test suite:

```bash
# Component tests
python test_build_components.py

# Run all tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

---

## 🔧 Configuration

Edit `config.yml` to customize:

```yaml
# LLM Settings
llm:
  provider: perplexity          # primary provider
  fallback: groq                # fallback provider
  model: sonar-pro              # specific model
  
# Generation Settings
generation:
  num_ideas: 50                 # ideas to generate
  temperature: 0.7              # creativity level
  
# Deployment
deployment:
  frontend: vercel              # frontend platform
  backend: render               # backend platform
```

---

## 📚 Advanced Usage

### Development Mode

```bash
# Verbose logging
python main.py generate -v

# Keep intermediate outputs
python main.py generate --verbose

# Test without code generation
python main.py generate --skip-code-gen
```

### Batch Processing

Generate multiple startups:

```bash
for i in {1..5}; do
  python main.py generate -o "./startup_$i"
done
```

### Custom Prompts

Edit generated `prompt.json` files and regenerate:

```bash
python main.py build-from-idea ideas.json -o ./my-startup
```

---

## 🤝 Contributing

Contributions welcome! Areas to help:

- [ ] Add more code templates
- [ ] Support additional LLM providers
- [ ] Improve deployment providers
- [ ] Add more UI themes
- [ ] Write documentation
- [ ] Report bugs

```bash
git clone https://github.com/taglia21/App-Builder.git
cd App-Builder
# Make your changes
git push origin feature-name
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## � Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](QUICK_START.md) | Get started in 2 minutes |
| [Development Guide](DEVELOPMENT.md) | Local setup and contribution |
| [API Reference](docs/API_REFERENCE.md) | Complete API documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design and modules |
| [Configuration](docs/CONFIGURATION.md) | Environment and settings |
| [Testing Guide](docs/TESTING.md) | Testing strategies and examples |
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | Cloud deployment instructions |

---

## 🙋 FAQ

**Q: Do I need API keys?**
A: Only if you want real AI features. Demo mode works without keys.

**Q: How long does code generation take?**
A: Typically 2-5 minutes depending on app complexity.

**Q: Can I customize the generated code?**
A: Absolutely! Generated code is yours to modify, deploy, sell.

**Q: What if I don't like the idea Ignara suggests?**
A: Use `build` mode to describe exactly what you want instead.

**Q: Is the generated code production-ready?**
A: Yes! It includes auth, validation, error handling, tests, and deployment config.

**Q: Can I use this to build side projects?**
A: Yes! Perfect for indie hackers, MVPs, and side hustles.

---

## 📞 Support

- 📖 Check [DEVELOPMENT.md](DEVELOPMENT.md) for setup help
- 🐛 Report bugs on GitHub Issues
- 💬 Discuss on GitHub Discussions
- 🚀 Share your generated apps!

---

## 🖥️ Web Dashboard

The built-in dashboard at `/build` lets you start pipeline builds from the browser. Progress is streamed in real-time via SSE — no page refreshes needed. Visit `/builds` to view history and download previous outputs.

```
uvicorn src.dashboard.app:app --reload
# then open http://localhost:8000/build
```

## 🔔 Notifications

Set `WEBHOOK_URL` or `DISCORD_WEBHOOK_URL` in your environment to receive build lifecycle events (started, stage changes, completed, failed). Webhook payloads are signed with HMAC-SHA256 via `WEBHOOK_SECRET`. See `.env.example` for all options.

## 🔌 Plugins

Extend the pipeline by subclassing `PluginBase` and decorating with `@register_plugin`. Hooks: `on_pipeline_start`, `on_stage_complete`, `on_pipeline_complete`, `on_error`. See `src/plugins/example_plugin.py` for a working example. Plugins are error-isolated — one failure never blocks others.

---

## 🎉 Next Steps

1. **Set your API key** (Perplexity or Groq)
2. **Run** `python main.py build`
3. **Describe your idea** in plain English
4. **Get your app** in minutes
5. **Deploy to cloud** with one command

**Happy building! 🚀**

---

<div align="center">

Made with ❤️ by the Ignara team

[Star on GitHub](https://github.com/taglia21/App-Builder) · [Get Perplexity Key](https://www.perplexity.ai/settings/api) · [Read Docs](docs/API_REFERENCE.md)

</div>
# Trigger deploy


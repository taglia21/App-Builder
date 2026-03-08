## 🚀 Ignara Quick Reference

### The Killer Feature: Interactive Build Mode

```bash
python main.py build
```

This is the recommended way to use Ignara. Users describe their idea, and Ignara:
1. Researches the market (Perplexity AI)
2. Asks smart follow-up questions
3. Generates a complete startup profile
4. Builds production-ready code

---

### Commands

| Command | Purpose |
|---------|---------|
| `build` | Interactive AI assistant (⭐ recommended) |
| `generate` | Full discovery pipeline |
| `build-from-idea` | Code from existing idea JSON |
| `deploy` | Deploy to cloud |
| `demo` | See example output |
| `providers` | Check LLM status |
| `test-llm` | Test API connectivity |

---

### Options

```bash
# LLM Provider
--llm-provider [auto|perplexity|groq|mock]

# Output
-o, --output ./path

# Theme
-t, --theme [Modern|Minimalist|Cyberpunk|Corporate]

# Controls
--demo                  # Use sample data
--skip-refinement       # Skip optimization
--skip-code-gen        # Stop after ideas
--deploy               # Auto-deploy

# Other
-v, --verbose          # Detailed logging
```

---

### Setup

```bash
# Install
pip install -r requirements.txt

# Get API key (free)
export PERPLEXITY_API_KEY="pplx-..."
export GROQ_API_KEY="gsk_..."  # optional

# Run
python main.py build
```

---

### Project Structure

```
src/
├── assistant.py       # ✨ Interactive assistant (killer feature!)
├── cli.py            # Command-line interface
├── pipeline.py       # Main orchestration
├── models.py         # Data structures
├── llm/              # LLM providers
├── code_generation/  # App generation
└── intelligence/     # Market research
```

---

### Testing

```bash
# Run tests
python test_build_components.py
pytest tests/

# Test with coverage
pytest --cov=src tests/
```

---

### Git

Latest commit: `2791d1f` - "feat: Add interactive AI assistant with 'build' command"

View all commits: `git log --oneline`

---

### Key Files

- [src/assistant.py](src/assistant.py) - Interactive assistant module
- [src/cli.py](src/cli.py) - CLI with build command
- [README.md](README.md) - Full documentation
- [config.yml](config.yml) - Configuration

---

### Examples

```python
# Import and use directly
from src import InteractiveAssistant

assistant = InteractiveAssistant()
success = assistant.run()
```

```bash
# Or use CLI
python main.py build --output ./my-app --theme Modern
```

---

### Troubleshooting

**No API key?** Use `--llm-provider mock` for demo mode

**Tests failing?** Run `python test_build_components.py` to verify setup

**Need help?** Check README.md or run `python main.py build --help`

---

### What Gets Generated

✓ FastAPI backend with JWT auth  
✓ Next.js frontend with 4 themes  
✓ PostgreSQL database with migrations  
✓ Docker configuration  
✓ API documentation (Swagger)  
✓ Tests and deployment config  

Ready to deploy immediately!

---

**Made with ❤️ by Ignara**

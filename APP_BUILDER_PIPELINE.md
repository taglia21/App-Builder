# App-Builder Pipeline Playbook

Quick reference for generating and running applications with the App-Builder.

## Pipeline Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Intelligence   │───▶│  Idea Generation │───▶│    Scoring      │
│  (Pain points)  │    │  (50+ concepts)  │    │  (Rank & filter)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Generated App   │◀───│ Code Generation  │◀───│ Prompt Engineer │
│ (Full codebase) │    │ (FastAPI+Next.js)│    │ (Spec creation) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Key Files:**
- `src/pipeline.py` - Main orchestration
- `src/code_generation/enhanced_engine.py` - Code generator
- `src/code_generation/file_templates.py` - Backend templates
- `src/code_generation/frontend_templates.py` - Frontend templates

---

## Generate a New App

### Option 1: Python One-Liner
```powershell
cd c:\Users\austi\OneDrive\Desktop\App-Builder\App-Builder
python -c "
from src.code_generation.enhanced_engine import EnhancedCodeGenerator
from src.models import ProductPrompt
import json, uuid

prompt = ProductPrompt(
    idea_id=uuid.uuid4(),
    idea_name='MyApp',
    prompt_content=json.dumps({
        'product_summary': {'solution_overview': 'Description of your app'}
    })
)
gen = EnhancedCodeGenerator()
gen.generate(prompt, './my_generated_app', 'Modern')
print('Done: ./my_generated_app')
"
```

### Option 2: Streamlit UI
```powershell
streamlit run streamlit_app.py
```
Then use the "High Priority Targets" tab to select an idea and generate code.

---

## Run a Generated App

### Prerequisites
- Docker Desktop installed and running
- Generated app directory (e.g., `./test_generated_app`)

### Start with Docker Compose
```powershell
cd .\test_generated_app
docker compose up --build
```

**Services after startup:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Stop Services
```powershell
docker compose down
```

---

## Run Generator Tests

### All Generator Tests
```powershell
pytest tests/test_generator.py -v
```

### Specific Regression Tests
```powershell
# CORS ordering (ensures _parse_cors_origins is defined before Settings class)
pytest tests/test_generator.py::TestGeneratedAppStructure::test_cors_function_defined_before_use -v

# Required startup files (docker-compose, Dockerfiles, .env, etc.)
pytest tests/test_generator.py::TestGeneratedAppStructure::test_app_has_required_startup_scripts -v
```

---

## Smoke Test a Generated App

Use the provided smoke test script to validate a generated app:

```powershell
.\scripts\smoke-test.ps1 .\test_generated_app
```

This script will:
1. Verify required files exist
2. Start docker-compose
3. Wait for backend to be healthy
4. Check `/health`, `/health/ready`, and `/health/live` endpoints

---

## Extend Templates

### Adding/Modifying Backend Templates
Edit `src/code_generation/file_templates.py`:
- Templates are Python string constants (e.g., `BACKEND_CONFIG_PY`)
- Use `${variable_name}` for substitution
- Keep functions **before** classes that use them

### Adding/Modifying Frontend Templates
Edit `src/code_generation/frontend_templates.py`:
- Same pattern as backend templates
- Components use TypeScript/React syntax

### After Template Changes
1. Run the test suite: `pytest tests/test_generator.py -v`
2. Generate a test app and verify it starts

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `NameError: name 'X' is not defined` | Check template for function/class ordering |
| Docker build timeout | Add `--default-timeout=1000` to pip install in Dockerfile |
| Missing module error | Add dependency to `backend/requirements.txt` template |
| Frontend build fails | Check `package.json` has all UI dependencies |
| Database connection failed | Wait for db healthcheck or increase retry count |

---

## Theme Options

When generating, you can specify a theme:
- `Modern` (default) - Clean, professional
- `Minimalist` - Simple, focused
- `Cyberpunk` - Neon/dark aesthetic
- `Corporate` - Business-oriented

```python
gen.generate(prompt, './output', theme='Cyberpunk')
```

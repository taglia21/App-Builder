"""Enhanced code generation engine for production-ready applications."""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from string import Template
from datetime import datetime
import ast
from src.llm.client import get_llm_client

from src.models import GeneratedCodebase, GoldStandardPrompt, ProductPrompt
from src.code_generation.file_templates import (
    BACKEND_MAIN_PY,
    BACKEND_CONFIG_PY,
    BACKEND_MODELS_USER_PY,
    BACKEND_MODELS_CORE_PY,
    BACKEND_SCHEMAS_USER_PY,
    BACKEND_SCHEMAS_CORE_PY,
    BACKEND_CRUD_BASE_PY,
    BACKEND_AUTH_PY,
    BACKEND_API_AUTH_PY,
    BACKEND_API_CRUD_PY,
    BACKEND_DB_SESSION_PY,
    BACKEND_DB_BASE_PY,
    BACKEND_TEST_AUTH_PY,
    BACKEND_TEST_CRUD_PY,
    GITHUB_WORKFLOW_CI,
    BACKEND_WORKER_PY,
    BACKEND_AI_SERVICE_PY,
    BACKEND_EMAIL_SERVICE_PY,
    BACKEND_EMAIL_SERVICE_PY,
    ROOT_DOCKER_COMPOSE
)
from src.deployment.providers import VercelProvider, RenderProvider
from src.deployment.infrastructure.ci_cd_generator import CICDGenerator
from src.deployment.infrastructure.terraform import TerraformGenerator
from src.deployment.models import DeploymentConfig, DeploymentProviderType
from src.code_generation.frontend_templates import (
    FRONTEND_UI_BUTTON,
    FRONTEND_UI_INPUT,
    FRONTEND_UI_CARD,
    FRONTEND_LIB_UTILS,
    FRONTEND_LOGIN_PAGE,
    FRONTEND_REGISTER_PAGE,
    FRONTEND_DASHBOARD_LAYOUT,
    FRONTEND_DASHBOARD_PAGE,
    FRONTEND_UI_TABLE,
    FRONTEND_UI_STATS_CARD,
    FRONTEND_COMPONENTS_SIDEBAR,
    FRONTEND_COMPONENTS_NAVBAR,
    FRONTEND_COMPONENTS_DATA_TABLE,
    FRONTEND_ENTITY_LIST_PAGE
)

logger = logging.getLogger(__name__)


class EnhancedCodeGenerator:
    """Generates complete, production-ready full-stack applications."""
    
    def __init__(self, config: Optional[Any] = None, llm_client: Optional[Any] = None):
        """Initialize with config (backward compatibility)."""
        # Config might be a PipelineConfig object or None
        output_dir = "./generated_app_v2"
        if config and hasattr(config, "code_generation") and config.code_generation:
             output_dir = config.code_generation.output_directory
        
        self.output_dir = Path(output_dir)
        self.files_created = []
        self.metrics = {
            'total_files': 0,
            'total_lines': 0,
            'backend_files': 0,
            'frontend_files': 0,
            'test_files': 0,
            'config_files': 0
        }
    
    def generate(self, prompt: Union[ProductPrompt, GoldStandardPrompt], output_dir: Optional[str] = None) -> GeneratedCodebase:
        """Generate complete application from startup idea."""
        
        # Determine output directory
        if output_dir:
            self.output_dir = Path(output_dir)
            
        # Extract idea details from Prompt object
        if isinstance(prompt, GoldStandardPrompt):
            product_prompt = prompt.product_prompt
        else:
            product_prompt = prompt
            
        idea_name = product_prompt.idea_name
        
        # Parse prompt content to get description/features
        try:
            content = json.loads(product_prompt.prompt_content)
            description = content.get("product_summary", {}).get("solution_overview", product_prompt.idea_name)
            if isinstance(description, dict):
                 description = str(description)
        except:
             description = product_prompt.idea_name
             
        # Mock Idea Dict for internal methods
        # Most internal methods use 'app_name' string directly, but _determine_core_entity uses 'idea' dict
        # We construct a synthetic idea dict
        idea_dict = {
            "name": idea_name,
            "solution_description": description,
            "one_liner": description
        }

        logger.info(f"Generating enhanced application for: {idea_name}")
        
        app_name = idea_name.replace(' ', '')
        
        # Determine core entity from idea
        entity = self._determine_core_entity(idea_dict)
        
        # Create directory structure
        self._create_directories()
        
        # transform idea to features
        # If technical_requirements are in prompt content, we should use them
        # For now, we rely on the description detection or pass specific flags if they exist
        features = self._detect_features(description)
        
        # Generate all files
        self._generate_backend(app_name, description, entity, features)
        self._generate_frontend(app_name, description, entity, theme="Modern") # theme is hardcoded for now
        self._generate_configs(app_name, description)
        self._generate_docs(app_name, description, entity)
        self._generate_docs(app_name, description, entity)
        self._generate_deployment_files(app_name, description)
        
        # Calculate metrics
        self._calculate_metrics()
        
        logger.info(f"✓ Generated {self.metrics['total_files']} files ({self.metrics['total_lines']} lines)")
        
        return GeneratedCodebase(
            idea_id=product_prompt.idea_id,
            idea_name=idea_name,
            output_path=str(self.output_dir),
            backend_framework="FastAPI",
            frontend_framework="Next.js 14",
            infrastructure_provider="Docker Compose",
            files_generated=self.metrics['total_files'],
            lines_of_code=self.metrics['total_lines']
        )

    
    def _detect_features(self, description: str) -> Dict[str, bool]:
        """Use LLM to detect necessary technical features."""
        try:
            client = get_llm_client("auto")
            prompt = f"""Analyze this app description and detect technical requirements.
Description: {description}

Return JSON boolean flags:
{{
    "needs_payments": true,  # If selling something/subscription
    "needs_background_jobs": true,  # If processing video/heavy data
    "needs_ai_integration": true,  # If usage of LLMs/AI is core
    "needs_email": true # If sending newsletters/notifications
}}
"""
            response = client.complete(prompt, json_mode=True)
            return json.loads(response.content.replace('```json', '').replace('```', '').strip())
        except Exception as e:
            logger.warning(f"Feature detection failed: {e}")
            return {
                "needs_payments": "subscription" in description.lower(),
                "needs_background_jobs": "video" in description.lower() or "scrape" in description.lower(),
                "needs_ai_integration": "ai" in description.lower(),
                "needs_email": "notify" in description.lower()
            }
    def _determine_core_entity(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the core entity for the app using LLM for smart modeling."""
        name = idea.get('name', 'Item')
        description = idea.get('solution_description', '')
        
        try:
            client = get_llm_client("auto")
            prompt = f"""Design the core database entity for this startup idea.
App Name: {name}
Description: {description}

Identify the SINGLE most important business object (e.g. for a Real Estate app -> 'Property', for a CRM -> 'Contact').
Return a strict JSON object with this structure:
{{
    "name": "ClassName",
    "class": "ClassName",
    "lower": "classname",
    "table": "table_names",
    "fields": [
        ["field_name", "String(255)", "str", true],
        ["description", "Text", "Optional[str]", false],
        ["status", "String(50)", "str", false],
        ["another_field", "Integer", "int", true]
    ]
}}
Rules:
1. 'fields' is a list of lists: [name, sql_type, python_type, required_bool]
2. sql_type examples: String(255), Text, Integer, Boolean, Float
3. python_type examples: str, int, bool, float, Optional[str]
4. Do not include 'id', 'created_at', 'updated_at' (added automatically).
5. detailed fields specific to the domain.
"""
            response = client.complete(prompt, json_mode=True)
            data = json.loads(response.content.replace('```json', '').replace('```', '').strip())
            
            # Validate structure
            if 'fields' in data and isinstance(data['fields'], list):
                return data
                
        except Exception as e:
            logger.warning(f"Smart entity determination failed: {e}. Falling back to heuristics.")

        # Fallback to heuristics if LLM fails
        combined_text = f"{name} {description}".lower()
        
        # Common entity patterns
        if any(w in combined_text for w in ['workflow', 'automation', 'flow', 'process']):
            return {
                'name': 'Workflow',
                'class': 'Workflow',
                'lower': 'workflow',
                'table': 'workflows',
                'fields': [
                    ('name', 'String(255)', 'str', True),
                    ('description', 'Text', 'Optional[str]', False),
                    ('is_active', 'Boolean', 'bool', False),
                    ('config', 'JSON', 'Optional[Dict]', False),
                ]
            }
        elif any(w in combined_text for w in ['project', 'task', 'manage', 'organize']):
            return {
                'name': 'Project',
                'class': 'Project',
                'lower': 'project',
                'table': 'projects',
                'fields': [
                    ('name', 'String(255)', 'str', True),
                    ('description', 'Text', 'Optional[str]', False),
                    ('status', 'String(50)', 'str', False),
                    ('priority', 'Integer', 'int', False),
                ]
            }
        elif any(w in combined_text for w in ['content', 'post', 'blog', 'article', 'document']):
            return {
                'name': 'Content',
                'class': 'Content',
                'lower': 'content',
                'table': 'contents',
                'fields': [
                    ('title', 'String(255)', 'str', True),
                    ('body', 'Text', 'str', True),
                    ('status', 'String(50)', 'str', False),
                    ('views', 'Integer', 'int', False),
                ]
            }
        else:
            # Default generic entity
            return {
                'name': 'Item',
                'class': 'Item',
                'lower': 'item',
                'table': 'items',
                'fields': [
                    ('name', 'String(255)', 'str', True),
                    ('description', 'Text', 'Optional[str]', False),
                    ('status', 'String(50)', 'str', False),
                    ('data', 'JSON', 'Optional[Dict]', False),
                ]
            }
    
    def _create_directories(self):
        """Create the directory structure."""
        dirs = [
            'backend/app/api/endpoints',
            'backend/app/core',
            'backend/app/crud',
            'backend/app/db',
            'backend/app/models',
            'backend/app/schemas',
            'backend/alembic/versions',
            'backend/tests/api',
            'frontend/src/app/(auth)/login',
            'frontend/src/app/(auth)/register',
            'frontend/src/app/(dashboard)/dashboard',
            'frontend/src/app/(dashboard)/dashboard/settings',
            'frontend/src/components/ui',
            'frontend/src/hooks',
            'frontend/src/lib',
            '.github/workflows',
            'docs',
        ]
        
        # Add entity directory to list
        # We can't access entity['lower'] here easily without passing it, 
        # but _generate_frontend handles the file creation which makes dirs implicitly if using write_file
        # so this list is just for initial structure.

        
        for d in dirs:
            (self.output_dir / d).mkdir(parents=True, exist_ok=True)
    
    def _write_file(self, path: str, content: str, category: str = 'config'):
        """Write a file and track it."""
        full_path = self.output_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            # Self-healing check for Python files
            if path.endswith('.py'):
                content = self._verify_and_fix(path, content)
            f.write(content)
        
        lines = len(content.split('\n'))
        self.files_created.append({
            'path': path,
            'lines': lines,
            'category': category
        })
        
        if category == 'backend':
            self.metrics['backend_files'] += 1
        elif category == 'frontend':
            self.metrics['frontend_files'] += 1
        elif category == 'test':
            self.metrics['test_files'] += 1
        else:
            self.metrics['config_files'] += 1

    def _verify_and_fix(self, path: str, content: str) -> str:
        """Verify Python syntax and fix with LLM if broken."""
        if not path.endswith('.py'):
            return content
            
        for attempt in range(3):
            try:
                ast.parse(content)
                return content
            except SyntaxError as e:
                logger.warning(f"Syntax error in {path} (Attempt {attempt+1}/3): {e}")
                try:
                    content = self._fix_code_with_llm(content, str(e))
                except Exception as llm_error:
                    logger.error(f"LLM fix failed: {llm_error}")
        
        # Final check
        try:
            ast.parse(content)
        except SyntaxError as e:
            logger.error(f"Failed to fix {path} after 3 attempts: {e}")
            
        return content

    def _fix_code_with_llm(self, code: str, error: str) -> str:
        """Use LLM to fix syntax error."""
        client = get_llm_client("auto")
        prompt = f"""Fix the following Python code which has a syntax error.
Error: {error}

Code:
```python
{code}
```

Return ONLY the fixed code. No explanations.
"""
        response = client.complete(prompt)
        # Clean response
        fixed = response.content.replace('```python', '').replace('```', '').strip()
        return fixed

    
    def _generate_backend(self, app_name: str, description: str, entity: Dict, features: Dict[str, bool] = None):
        """Generate all backend files."""
        features = features or {}
        db_name = app_name.lower().replace('-', '_')
        
        # Main app
        content = Template(BACKEND_MAIN_PY).safe_substitute(
            app_name=app_name,
            description=description
        )
        self._write_file('backend/app/main.py', content, 'backend')
        
        # Config
        content = Template(BACKEND_CONFIG_PY).safe_substitute(
            app_name=app_name,
            db_name=db_name
        )
        self._write_file('backend/app/core/config.py', content, 'backend')
        
        # Auth
        self._write_file('backend/app/core/auth.py', BACKEND_AUTH_PY, 'backend')
        self._write_file('backend/app/core/__init__.py', '', 'backend')
        
        # Database
        self._write_file('backend/app/db/session.py', BACKEND_DB_SESSION_PY, 'backend')
        self._write_file('backend/app/db/base_class.py', BACKEND_DB_BASE_PY, 'backend')
        self._write_file('backend/app/db/__init__.py', f'from app.db.base_class import Base  # noqa', 'backend')
        
        # Dynamic Modules (Smart Templates)
        if features.get('needs_payments'):
            logger.info("Injecting Payment Module (Stripe)...")
            try:
                client = get_llm_client("auto")
                prompt = "Write a production-ready Python FastAPI module using 'stripe' library. It should include a 'create_checkout_session' function and a webhook handler. Return only python code."
                resp = client.complete(prompt)
                payment_code = resp.content.replace('```python', '').replace('```', '')
                self._write_file('backend/app/core/payment.py', payment_code, 'backend')
            except Exception as e:
                logger.error(f"Failed to generate payment module: {e}")
        
        # Models
        user_model = Template(BACKEND_MODELS_USER_PY).safe_substitute(
            relationships=f'{entity["table"]} = relationship("{entity["class"]}", back_populates="owner")'
        )
        self._write_file('backend/app/models/user.py', user_model, 'backend')
        
        # Generate columns for entity model
        columns = []
        for field_name, sql_type, py_type, required in entity['fields']:
            nullable = 'False' if required else 'True'
            columns.append(f'{field_name} = Column({sql_type}, nullable={nullable})')
        
        entity_model = Template(BACKEND_MODELS_CORE_PY).safe_substitute(
            entity_name=entity['name'],
            entity_class=entity['class'],
            table_name=entity['table'],
            columns='\n    '.join(columns)
        )
        self._write_file(f'backend/app/models/{entity["lower"]}.py', entity_model, 'backend')
        self._write_file('backend/app/models/__init__.py', 
                        f'from app.models.user import User  # noqa\nfrom app.models.{entity["lower"]} import {entity["class"]}  # noqa', 
                        'backend')
        
        # Schemas
        self._write_file('backend/app/schemas/user.py', BACKEND_SCHEMAS_USER_PY, 'backend')
        
        # Generate schema fields
        schema_fields = []
        update_fields = []
        for field_name, sql_type, py_type, required in entity['fields']:
            if required:
                schema_fields.append(f'{field_name}: {py_type}')
            else:
                schema_fields.append(f'{field_name}: {py_type} = None')
            update_fields.append(f'{field_name}: {py_type} = None')
        
        entity_schema = Template(BACKEND_SCHEMAS_CORE_PY).safe_substitute(
            entity_name=entity['name'],
            entity_class=entity['class'],
            schema_fields='\n    '.join(schema_fields),
            update_fields='\n    '.join(update_fields)
        )
        self._write_file(f'backend/app/schemas/{entity["lower"]}.py', entity_schema, 'backend')
        self._write_file('backend/app/schemas/__init__.py', '', 'backend')
        
        # CRUD
        self._write_file('backend/app/crud/base.py', BACKEND_CRUD_BASE_PY, 'backend')
        entity_crud = f'''"""CRUD operations for {entity['class']}."""

from app.crud.base import CRUDBase
from app.models.{entity['lower']} import {entity['class']}
from app.schemas.{entity['lower']} import {entity['class']}Create, {entity['class']}Update

class CRUD{entity['class']}(CRUDBase[{entity['class']}, {entity['class']}Create, {entity['class']}Update]):
    pass

crud_{entity['lower']} = CRUD{entity['class']}({entity['class']})
'''
        self._write_file(f'backend/app/crud/{entity["lower"]}.py', entity_crud, 'backend')
        self._write_file('backend/app/crud/__init__.py', '', 'backend')
        
        # API endpoints
        self._write_file('backend/app/api/endpoints/auth.py', BACKEND_API_AUTH_PY, 'backend')
        
        entity_api = Template(BACKEND_API_CRUD_PY).safe_substitute(
            entity_name=entity['name'],
            entity_class=entity['class'],
            entity_lower=entity['lower']
        )
        self._write_file(f'backend/app/api/endpoints/{entity["lower"]}s.py', entity_api, 'backend')
        self._write_file('backend/app/api/endpoints/__init__.py', '', 'backend')
        
        # API router
        api_router = f'''"""API router."""

from fastapi import APIRouter
from app.api.endpoints import auth, {entity['lower']}s

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router({entity['lower']}s.router, prefix="/{entity['lower']}s", tags=["{entity['lower']}s"])
'''
        self._write_file('backend/app/api/__init__.py', api_router, 'backend')
        self._write_file('backend/app/__init__.py', '', 'backend')
        
        # Requirements
        requirements = '''fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
redis==5.0.1
httpx==0.26.0
pytest==7.4.4
pytest-asyncio==0.23.3
'''
        if features.get('needs_payments'):
            requirements += "stripe==7.0.0\n"
        if features.get('needs_background_jobs'):
            requirements += "celery==5.3.6\nflower==2.0.1\n"
        if features.get('needs_ai_integration'):
            requirements += "openai==1.10.0\nanthropic==0.10.0\n"
        if features.get('needs_email'):
            requirements += "fastapi-mail==1.4.1\n"
            
        self._write_file('backend/requirements.txt', requirements, 'backend')
        
        # Dockerfile
        dockerfile = '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
'''
        self._write_file('backend/Dockerfile', dockerfile, 'backend')
        
        # Tests
        self._write_file('backend/tests/api/test_auth.py', BACKEND_TEST_AUTH_PY, 'test')
        
        test_fields = [f'"{field_name}": "test"' for field_name, _, py_type, req in entity['fields'][:2] if req]
        crud_tests = Template(BACKEND_TEST_CRUD_PY).safe_substitute(
            entity_class=entity['class'],
            entity_lower=entity['lower'],
            test_create_json=', '.join(test_fields) if test_fields else '"name": "test"'
        )
        self._write_file(f'backend/tests/api/test_{entity["lower"]}s.py', crud_tests, 'test')
        
        conftest = '''"""Pytest configuration."""
import pytest

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
'''
        self._write_file('backend/tests/conftest.py', conftest, 'test')
        self._write_file('backend/tests/__init__.py', '', 'test')
        self._write_file('backend/tests/api/__init__.py', '', 'test')

        # Additional Features
        if features.get('needs_background_jobs'):
            self._generate_background_jobs(app_name)
            
        if features.get('needs_ai_integration'):
            self._generate_ai_service(app_name)
            
        if features.get('needs_email'):
            self._generate_email_service(app_name)

    def _generate_background_jobs(self, app_name: str):
        """Generate Celery worker configuration."""
        logger.info("Generating background jobs module...")
        self._write_file('backend/app/worker.py', BACKEND_WORKER_PY, 'backend')
        self._write_file('backend/app/celery_app.py', 'from app.worker import celery_app', 'backend')

    def _generate_ai_service(self, app_name: str):
        """Generate AI service module."""
        logger.info("Generating AI service...")
        self._write_file('backend/app/services/ai.py', BACKEND_AI_SERVICE_PY, 'backend')
        self._write_file('backend/app/services/__init__.py', '', 'backend')

    def _generate_email_service(self, app_name: str):
        """Generate Email service module."""
        logger.info("Generating email service...")
        self._write_file('backend/app/services/email.py', BACKEND_EMAIL_SERVICE_PY, 'backend')

    def _generate_deployment_files(self, app_name: str, description: str):
        """Generate all deployment configuration files."""
        logger.info("Generating deployment configurations...")
        
        # 1. Vercel Config (Frontend)
        # We instantiate provider to use its config generation logic
        vercel = VercelProvider()
        # Mock config for generation purposes
        v_config = DeploymentConfig(provider=DeploymentProviderType.VERCEL, region="iad1")
        vercel._generate_vercel_config(self.output_dir / "frontend", v_config)
        self.files_created.append({'path': 'frontend/vercel.json', 'lines': 10, 'category': 'config'})
        
        # 2. Render Config (Backend)
        render = RenderProvider()
        r_config = DeploymentConfig(provider=DeploymentProviderType.RENDER)
        # We need to simulate the path expected by render provider (it expects root usually or we pass backend path?)
        # BaseDeploymentProvider logic usually expects 'codebase_path'.
        # RenderProvider._generate_render_yaml writes to codebase_path / render.yaml
        # We want it in root or backend? Usually root for monorepo or specific if separated.
        # Let's put it in root for now as 'render.yaml' often defines services for subdirs.
        render._generate_render_yaml(self.output_dir, r_config)
        self.files_created.append({'path': 'render.yaml', 'lines': 20, 'category': 'config'})
        
        # 3. CI/CD Pipeline
        cicd = CICDGenerator()
        cicd.generate_github_actions(self.output_dir)
        self.files_created.append({'path': '.github/workflows/deploy.yml', 'lines': 30, 'category': 'config'})
        
        # 4. Terraform Templates
        tf = TerraformGenerator()
        tf.generate_templates(self.output_dir)
        self.files_created.append({'path': 'terraform/main.tf', 'lines': 20, 'category': 'config'})
        
        # 5. Deployment Guide
        guide = f"""# Deployment Guide for {app_name}

## 🚀 Quick Start (Automated)

You can deploy this application using the App-Builder CLI:

```bash
python main.py deploy ./generated_app_v2 --frontend vercel --backend render
```

## 🛠 Manual Deployment

### Frontend (Vercel)
1. Install CLI: `npm i -g vercel`
2. Login: `vercel login`
3. Deploy: `cd frontend && vercel`

### Backend (Render)
1. Create a Web Service for `backend/` (Python/FastAPI).
2. Create a PostgreSQL database.
3. Set `DATABASE_URL` environment variable.

### Infrastructure (Terraform)
Templates are available in `terraform/` directory for AWS provisioning.
"""
        self._write_file('DEPLOYMENT_GUIDE.md', guide, 'docs')
    
    
    def _get_theme_config(self, theme: str = "Modern") -> Dict[str, str]:
        """Get CSS variables and config for selected theme."""
        themes = {
            "Modern": {
                "radius": "0.5rem",
                "font": "Inter, sans-serif",
                "colors": """
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;"""
            },
            "Minimalist": {
                "radius": "0rem",
                "font": "Helvetica Neue, sans-serif",
                "colors": """
    --background: 0 0% 100%;
    --foreground: 0 0% 0%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --input: 0 0% 90%;
    --ring: 0 0% 70%;"""
            },
            "Cyberpunk": {
                "radius": "0px",
                "font": "Orbitron, sans-serif",
                "colors": """
    --background: 260 50% 10%;
    --foreground: 280 80% 80%;
    --primary: 320 100% 50%;
    --primary-foreground: 0 0% 0%;
    --secondary: 180 100% 50%;
    --secondary-foreground: 0 0% 0%;
    --input: 260 50% 20%;
    --ring: 320 100% 50%;"""
            },
            "Corporate": {
                "radius": "0.25rem",
                "font": "Arial, sans-serif",
                "colors": """
    --background: 220 30% 96%;
    --foreground: 220 50% 20%;
    --primary: 220 80% 40%;
    --primary-foreground: 0 0% 100%;
    --secondary: 210 20% 90%;
    --secondary-foreground: 220 50% 20%;
    --input: 220 20% 85%;
    --ring: 220 80% 40%;"""
            }
        }
        return themes.get(theme, themes["Modern"])

    def _generate_frontend_types(self, entity: Dict[str, Any]) -> None:
        """
        Generate TypeScript interfaces from backend entity definition.
        Ensures Contract-First reliability.
        """
        logger.info("Generating TypeScript schema (Contract-First)...")
        
        name = entity.get('name', 'Entity')
        fields = entity.get('fields', [])
        
        # Type mapping
        type_map = {
            'String': 'string',
            'Text': 'string',
            'Integer': 'number',
            'Float': 'number',
            'Boolean': 'boolean',
            'DateTime': 'string',
            'Date': 'string'
        }
        
        lines = []
        lines.append("// This file is auto-generated by the App-Builder Contract System")
        lines.append("// It must match the backend Pydantic models.")
        lines.append("")
        
        lines.append(f"export interface {name} {{")
        lines.append("  id: string;") # UUID default
        
        for field in fields:
            # Handle List/Tuple format from _determine_core_entity
            # [name, sql_type, python_type, is_required]
            if isinstance(field, (list, tuple)) and len(field) >= 2:
                f_name = field[0]
                sql_type = field[1]
                # is_required is index 3 if exists, default True? 
                # looking at fallback: ('status', 'String', 'str', False) -> False means not required?
                # No, standard is usually (name, type, pytype, required).
                # Fallback 'description' is Optional[str] and False. So False = Not Required (Nullable).
                # Fallback 'name' is str and True. So True = Required (Not Nullable).
                is_required = field[3] if len(field) > 3 else False
                is_nullable = not is_required
                
                # Normalize SQL Type to TS Type
                ts_type = 'any'
                st_lower = sql_type.lower()
                if 'int' in st_lower or 'float' in st_lower or 'numeric' in st_lower:
                    ts_type = 'number'
                elif 'bool' in st_lower:
                    ts_type = 'boolean'
                elif 'json' in st_lower:
                    ts_type = 'any'
                else:
                    # String, Text, Date, etc
                    ts_type = 'string'
                
                suffix = "?" if is_nullable else ""
                lines.append(f"  {f_name}{suffix}: {ts_type};")

            elif isinstance(field, dict):
                 # Fallback for dictionary format (if ever used)
                f_name = field.get('name')
                f_type = field.get('type', 'String')
                is_nullable = field.get('nullable', False)
                ts_type = type_map.get(f_type, 'string') # Usage dependent
                suffix = "?" if is_nullable else ""
                lines.append(f"  {f_name}{suffix}: {ts_type};")
            
        lines.append("  created_at?: string;")
        lines.append("}")
        
        # Write file
        content = "\n".join(lines)
        self._write_file("frontend/src/types/schema.ts", content, "frontend")

    def _generate_frontend(self, app_name: str, description: str, entity: Dict, theme: str = "Modern"):
        """Generate minimal but functional frontend."""
        
        # Generate Types (Contract-First)
        self._generate_frontend_types(entity)

        theme_config = self._get_theme_config(theme)

        # Package.json

        package_json = f'''{{
  "name": "{app_name.lower().replace(' ', '-')}",
  "version": "1.0.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "axios": "^1.6.5",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "lucide-react": "^0.309.0",
    "recharts": "^2.10.4",
    "react-hook-form": "^7.49.3",
    "zod": "^3.22.4",
    "@hookform/resolvers": "^3.3.4",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-label": "^2.0.2",
    "@tanstack/react-table": "^8.11.7",
    "class-variance-authority": "^0.7.0"
  }},
  "devDependencies": {{
    "@types/node": "20.11.5",
    "@types/react": "18.2.48",
    "@types/react-dom": "18.2.17",
    "typescript": "5.3.3",
    "tailwindcss": "3.4.1",
    "autoprefixer": "10.4.17",
    "postcss": "8.4.33"
  }}
}}
'''
        self._write_file('frontend/package.json', package_json, 'frontend')
        
        # Next.js Config
        next_config = '''/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
};

export default nextConfig;
'''
        self._write_file('frontend/next.config.mjs', next_config, 'frontend')
        
        # Globals CSS
        globals_css = f'''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {{
  :root {{
    {theme_config['colors']}
    --radius: {theme_config['radius']};
  }}
}}

@layer base {{
  * {{
    @apply border-border;
  }}
  body {{
    @apply bg-background text-foreground;
    font-family: {theme_config['font']};
  }}
}}
'''
        self._write_file('frontend/src/app/globals.css', globals_css, 'frontend')
        
        # Tailwind Config
        tailwind_config = '''import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--input))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};
export default config;
'''
        self._write_file('frontend/tailwind.config.ts', tailwind_config, 'frontend')

        # Home page
        home_page = f'''export default function Home() {{
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-6 p-8 border rounded-lg shadow-lg bg-card text-card-foreground max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight text-primary">{app_name}</h1>
        <p className="text-xl text-muted-foreground">{description}</p>
        <div className="flex justify-center gap-4">
          <a href="/login" className="px-8 py-3 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition font-medium">
            Get Started
          </a>
          <a href="/docs" className="px-8 py-3 bg-secondary text-secondary-foreground rounded-md hover:opacity-90 transition font-medium">
            Documentation
          </a>
        </div>
      </div>
    </div>
  );
}}
'''
        self._write_file('frontend/src/app/page.tsx', home_page, 'frontend')
        
        # Layout
        layout = f'''import type {{ Metadata }} from "next";
import "./globals.css";

export const metadata: Metadata = {{
  title: "{app_name}",
  description: "{description}",
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  );
}}
'''
        self._write_file('frontend/src/app/layout.tsx', layout, 'frontend')
        
        # Dockerfile
        frontend_dockerfile = '''FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]
'''
        self._write_file('frontend/Dockerfile', frontend_dockerfile, 'frontend')
        
        # tsconfig
        tsconfig = '''{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./src/*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
'''
        self._write_file('frontend/tsconfig.json', tsconfig, 'frontend')
    
        # Components
        self._write_file('frontend/src/components/ui/button.tsx', FRONTEND_UI_BUTTON, 'frontend')
        self._write_file('frontend/src/components/ui/input.tsx', FRONTEND_UI_INPUT, 'frontend')
        self._write_file('frontend/src/components/ui/card.tsx', FRONTEND_UI_CARD, 'frontend')
        self._write_file('frontend/src/components/ui/table.tsx', FRONTEND_UI_TABLE, 'frontend')
        self._write_file('frontend/src/components/ui/stats-card.tsx', FRONTEND_UI_STATS_CARD, 'frontend')
        self._write_file('frontend/src/components/ui/data-table.tsx', FRONTEND_COMPONENTS_DATA_TABLE, 'frontend')
        self._write_file('frontend/src/components/ui/label.tsx', 'export * from "@radix-ui/react-label"', 'frontend')
        self._write_file('frontend/src/components/sidebar.tsx', Template(FRONTEND_COMPONENTS_SIDEBAR).safe_substitute(app_name=app_name, entity_name=entity['name'], entity_lower=entity['lower']), 'frontend')
        self._write_file('frontend/src/components/navbar.tsx', FRONTEND_COMPONENTS_NAVBAR, 'frontend')
        self._write_file('frontend/src/components/ui/alert.tsx', 'import * as React from "react"\\nimport { cva, type VariantProps } from "class-variance-authority"\\nimport { cn } from "@/lib/utils"\\n\\nconst alertVariants = cva(\\n  "relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground",\\n  {\\n    variants: {\\n      variant: {\\n        default: "bg-background text-foreground",\\n        destructive:\\n          "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",\\n      },\\n    },\\n    defaultVariants: {\\n      variant: "default",\\n    },\\n  }\\n)\\n\\nconst Alert = React.forwardRef<\\n  HTMLDivElement,\\n  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>\\n>(({ className, variant, ...props }, ref) => (\\n  <div\\n    ref={ref}\\n    role="alert"\\n    className={cn(alertVariants({ variant }), className)}\\n    {...props}\\n  />\\n))\\nAlert.displayName = "Alert"\\n\\nconst AlertTitle = React.forwardRef<\\n  HTMLParagraphElement,\\n  React.HTMLAttributes<HTMLHeadingElement>\\n>(({ className, ...props }, ref) => (\\n  <h5\\n    ref={ref}\\n    className={cn("mb-1 font-medium leading-none tracking-tight", className)}\\n    {...props}\\n  />\\n))\\nAlertTitle.displayName = "AlertTitle"\\n\\nconst AlertDescription = React.forwardRef<\\n  HTMLParagraphElement,\\n  React.HTMLAttributes<HTMLParagraphElement>\\n>(({ className, ...props }, ref) => (\\n  <div\\n    ref={ref}\\n    className={cn("text-sm [&_p]:leading-relaxed", className)}\\n    {...props}\\n  />\\n))\\nAlertDescription.displayName = "AlertDescription"\\n\\nexport { Alert, AlertTitle, AlertDescription }', 'frontend')
        self._write_file('frontend/src/lib/utils.ts', FRONTEND_LIB_UTILS, 'frontend')
        
        # Icons
        icons_comp = '''import { Loader2 } from "lucide-react";

export const Icons = {
  spinner: Loader2,
};
'''
        self._write_file('frontend/src/components/icons.tsx', icons_comp, 'frontend')

        # Authentication
        self._write_file('frontend/src/app/(auth)/login/page.tsx', FRONTEND_LOGIN_PAGE, 'frontend')
        self._write_file('frontend/src/app/(auth)/register/page.tsx', FRONTEND_REGISTER_PAGE, 'frontend')
        self._write_file('frontend/src/app/(auth)/layout.tsx', 'export default function AuthLayout({children}: {children: React.ReactNode}) { return children }', 'frontend')

        # Dashboard
        dashboard_layout = FRONTEND_DASHBOARD_LAYOUT # It handles its own imports now via components
        self._write_file('frontend/src/app/(dashboard)/layout.tsx', dashboard_layout, 'frontend')
        
        dashboard_page = Template(FRONTEND_DASHBOARD_PAGE).safe_substitute(
            entity_name=entity['name'],
            entity_lower=entity['lower']
        )
        self._write_file('frontend/src/app/(dashboard)/dashboard/page.tsx', dashboard_page, 'frontend')
        self._write_file('frontend/src/app/(dashboard)/dashboard/settings/page.tsx', 'export default function Settings() { return <div>Settings</div> }', 'frontend')
        
        # Entity Pages
        entity_list_page = Template(FRONTEND_ENTITY_LIST_PAGE).safe_substitute(
            entity_name=entity['name'],
            entity_lower=entity['lower']
        )
        self._write_file(f'frontend/src/app/(dashboard)/dashboard/{entity["lower"]}s/page.tsx', entity_list_page, 'frontend')
    
    def _generate_configs(self, app_name: str, description: str):
        """Generate configuration files."""
        # Docker Compose
        docker_compose = f'''version: "3.8"

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {app_name.lower().replace(' ', '_').replace('-', '_')}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/{app_name.lower().replace(' ', '_').replace('-', '_')}
      SECRET_KEY: dev-secret-key
    depends_on:
      - db
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
'''
        self._write_file('docker-compose.yml', docker_compose, 'config')
        
        # .gitignore
        gitignore = '''node_modules/
__pycache__/
*.pyc
.env
.next/
dist/
*.log
.DS_Store
'''
        self._write_file('.gitignore', gitignore, 'config')
        
        # CI/CD
        self._write_file('.github/workflows/ci.yml', GITHUB_WORKFLOW_CI, 'config')
    
    def _generate_docs(self, app_name: str, description: str, entity: Dict):
        """Generate documentation."""
        readme = f'''# {app_name}

{description}

## Quick Start

```bash
# Start all services
docker-compose up -d

# Access
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000/docs
```

## Features

- ✅ JWT Authentication
- ✅ Full CRUD for {entity['name']}s
- ✅ PostgreSQL Database
- ✅ REST API with FastAPI
- ✅ Next.js Frontend
- ✅ Docker Setup
- ✅ Test Suite

## API Endpoints

- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/{entity['lower']}s/` - List {entity['lower']}s
- `POST /api/v1/{entity['lower']}s/` - Create {entity['lower']}
- `GET /api/v1/{entity['lower']}s/{{id}}` - Get {entity['lower']}
- `PUT /api/v1/{entity['lower']}s/{{id}}` - Update {entity['lower']}
- `DELETE /api/v1/{entity['lower']}s/{{id}}` - Delete {entity['lower']}

## Tech Stack

**Backend:**
- FastAPI 0.109
- SQLAlchemy 2.0
- PostgreSQL 15
- JWT Auth
- Pytest

**Frontend:**
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS

Generated by AI Startup Generator
'''
        self._write_file('README.md', readme, 'config')


    
    def _calculate_metrics(self):
        """Calculate generation metrics."""
        self.metrics['total_files'] = len(self.files_created)
        self.metrics['total_lines'] = sum(f['lines'] for f in self.files_created)

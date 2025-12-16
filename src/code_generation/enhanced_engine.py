"""Enhanced code generation engine for production-ready applications."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from string import Template
from datetime import datetime

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
    GITHUB_WORKFLOW_CI
)

logger = logging.getLogger(__name__)


class EnhancedCodeGenerator:
    """Generates complete, production-ready full-stack applications."""
    
    def __init__(self, output_dir: str = "./generated_app_v2"):
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
    
    def generate(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete application from startup idea."""
        logger.info(f"Generating enhanced application for: {idea.get('name', 'App')}")
        
        # Extract idea details
        app_name = idea.get('name', 'MyApp').replace(' ', '')
        description = idea.get('solution_description', idea.get('one_liner', 'A modern web application'))[:200]
        
        # Determine core entity from idea
        entity = self._determine_core_entity(idea)
        
        # Create directory structure
        self._create_directories()
        
        # Generate all files
        self._generate_backend(app_name, description, entity)
        self._generate_frontend(app_name, description, entity)
        self._generate_configs(app_name, description)
        self._generate_docs(app_name, description, entity)
        
        # Calculate metrics
        self._calculate_metrics()
        
        logger.info(f"✓ Generated {self.metrics['total_files']} files ({self.metrics['total_lines']} lines)")
        
        return {
            'output_dir': str(self.output_dir),
            'files': self.files_created,
            'metrics': self.metrics
        }
    
    def _determine_core_entity(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the core entity for the app based on the idea."""
        name = idea.get('name', 'Item').lower()
        problem = idea.get('problem_statement', '').lower()
        solution = idea.get('solution_description', '').lower()
        
        combined_text = f"{name} {problem} {solution}"
        
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
            'frontend/src/components/ui',
            'frontend/src/hooks',
            'frontend/src/lib',
            '.github/workflows',
            'docs',
        ]
        
        for d in dirs:
            (self.output_dir / d).mkdir(parents=True, exist_ok=True)
    
    def _write_file(self, path: str, content: str, category: str = 'config'):
        """Write a file and track it."""
        full_path = self.output_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
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
    
    def _generate_backend(self, app_name: str, description: str, entity: Dict):
        """Generate all backend files."""
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
    
    def _generate_frontend(self, app_name: str, description: str, entity: Dict):
        """Generate minimal but functional frontend."""
        
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
    "axios": "^1.6.5"
  }},
  "devDependencies": {{
    "@types/node": "20.11.5",
    "@types/react": "18.2.48",
    "typescript": "5.3.3",
    "tailwindcss": "3.4.1",
    "autoprefixer": "10.4.17",
    "postcss": "8.4.33"
  }}
}}
'''
        self._write_file('frontend/package.json', package_json, 'frontend')
        
        # Home page
        home_page = f'''export default function Home() {{
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">{app_name}</h1>
        <p className="text-gray-600 mb-8">{description}</p>
        <div className="space-x-4">
          <a href="/login" className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Sign In
          </a>
          <a href="/register" className="px-6 py-2 bg-gray-200 rounded hover:bg-gray-300">
            Sign Up
          </a>
        </div>
      </div>
    </div>
  );
}}
'''
        self._write_file('frontend/src/app/page.tsx', home_page, 'frontend')
        
        # Layout
        layout = f'''export const metadata = {{
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

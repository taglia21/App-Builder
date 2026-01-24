"""
Code Generation Engine
Generates complete, production-ready codebases from product specifications.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.models import ProductPrompt, GeneratedCodebase, GoldStandardPrompt
from src.config import PipelineConfig
from src.llm import get_llm_client
from src.llm.client import BaseLLMClient

logger = logging.getLogger(__name__)


class CodeGenerationEngine:
    """
    Generates complete codebases from product specifications.
    
    Outputs:
    - Backend (FastAPI)
    - Frontend (Next.js)
    - Docker configuration
    - Documentation
    """
    
    def __init__(self, config: PipelineConfig, llm_client: Optional[BaseLLMClient] = None):
        self.config = config
        self.llm_client = llm_client or get_llm_client()
    
    def generate(
        self,
        prompt: ProductPrompt,
        output_dir: str = "./generated_project"
    ) -> GeneratedCodebase:
        """
        Generate a complete codebase from a product prompt.
        
        Args:
            prompt: The product specification
            output_dir: Directory to write generated files
            
        Returns:
            GeneratedCodebase with metadata about generated files
        """
        logger.info(f"Generating codebase for: {prompt.idea_name}")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files_generated = 0
        lines_of_code = 0
        
        # Generate project structure
        logger.info("Generating project files...")
        files_generated += self._generate_readme(prompt, output_path)
        files_generated += self._generate_docker_compose(prompt, output_path)
        files_generated += self._generate_gitignore(output_path)
        files_generated += self._generate_env_example(prompt, output_path)
        
        # Generate backend
        logger.info("Generating backend structure...")
        backend_path = output_path / "backend"
        backend_path.mkdir(exist_ok=True)
        files_generated += self._generate_backend_requirements(backend_path)
        files_generated += self._generate_backend_dockerfile(backend_path)
        files_generated += self._generate_backend_main(prompt, backend_path)
        
        # Generate frontend
        logger.info("Generating frontend structure...")
        frontend_path = output_path / "frontend"
        frontend_path.mkdir(exist_ok=True)
        files_generated += self._generate_frontend_package_json(prompt, frontend_path)
        files_generated += self._generate_frontend_dockerfile(frontend_path)
        
        # Generate documentation
        logger.info("Generating documentation...")
        docs_path = output_path / "docs"
        docs_path.mkdir(exist_ok=True)
        files_generated += self._generate_architecture_doc(prompt, docs_path)
        
        logger.info(f"Generated {files_generated} files")
        
        return GeneratedCodebase(
            idea_id=prompt.idea_id,
            idea_name=prompt.idea_name,
            output_path=str(output_path),
            backend_framework="FastAPI",
            frontend_framework="Next.js",
            infrastructure_provider="Docker",
            files_generated=files_generated,
            lines_of_code=lines_of_code
        )
    
    def _generate_readme(self, prompt: ProductPrompt, output_path: Path) -> int:
        """Generate README.md"""
        project_name = prompt.idea_name.lower().replace(" ", "_")
        
        # Parse prompt_content
        try:
            content_dict = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            content_dict = {}
        
        tagline = content_dict.get('product_summary', {}).get('tagline', 'A modern SaaS application')
        
        content = f"""# {prompt.idea_name}

{tagline}

## Overview

Generated using App-Builder Pipeline

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Next.js 14 (TypeScript)
- **Database**: PostgreSQL
- **Cache**: Redis

## Quick Start

```bash
# Start with Docker Compose
docker-compose up -d

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## Documentation

See `/docs` for detailed documentation.

## License

MIT License
"""
        (output_path / "README.md").write_text(content)
        return 1
    
    def _generate_docker_compose(self, prompt: ProductPrompt, output_path: Path) -> int:
        """Generate docker-compose.yml"""
        project_name = prompt.idea_name.lower().replace(" ", "_").replace("-", "_")
        
        content = f"""version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/{project_name}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB={project_name}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
"""
        (output_path / "docker-compose.yml").write_text(content)
        return 1
    
    def _generate_gitignore(self, output_path: Path) -> int:
        """Generate .gitignore"""
        content = """# Python
__pycache__/
*.py[cod]
venv/
.env

# Node
node_modules/
.next/
out/

# IDE
.idea/
.vscode/

# OS
.DS_Store

# Logs
*.log

# Build
dist/
build/
"""
        (output_path / ".gitignore").write_text(content)
        return 1
    
    def _generate_env_example(self, prompt: ProductPrompt, output_path: Path) -> int:
        """Generate .env.example"""
        project_name = prompt.idea_name.lower().replace(" ", "_").replace("-", "_")
        
        content = f"""# Application
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
DEBUG=true

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/{project_name}

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

# External Services (optional)
STRIPE_SECRET_KEY=
OPENAI_API_KEY=
"""
        (output_path / ".env.example").write_text(content)
        return 1
    
    def _generate_backend_requirements(self, backend_path: Path) -> int:
        """Generate backend/requirements.txt"""
        content = """# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
email-validator>=2.1.0
python-dotenv>=1.0.0

# Database
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Redis
redis>=5.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
"""
        (backend_path / "requirements.txt").write_text(content)
        return 1
    
    def _generate_backend_dockerfile(self, backend_path: Path) -> int:
        """Generate backend/Dockerfile"""
        content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl for healthchecks, libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    gcc \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        (backend_path / "Dockerfile").write_text(content)
        return 1
    
    def _generate_backend_main(self, prompt: ProductPrompt, backend_path: Path) -> int:
        """Generate backend/app/main.py"""
        app_path = backend_path / "app"
        app_path.mkdir(exist_ok=True)
        
        content = f'''"""
Main FastAPI Application for {prompt.idea_name}
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{prompt.idea_name}",
    description="Generated by App-Builder Pipeline",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {{"message": "Welcome to {prompt.idea_name} API"}}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{"status": "healthy", "version": "1.0.0"}}
'''
        (app_path / "main.py").write_text(content)
        (app_path / "__init__.py").write_text("")
        return 2
    
    def _generate_frontend_package_json(self, prompt: ProductPrompt, frontend_path: Path) -> int:
        """Generate frontend/package.json"""
        content = f'''{{"name": "frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "^14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }},
  "devDependencies": {{
    "typescript": "^5.3.0",
    "@types/node": "^20.11.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.56.0",
    "eslint-config-next": "^14.1.0"
  }}
}}'''
        (frontend_path / "package.json").write_text(content)
        return 1
    
    def _generate_frontend_dockerfile(self, frontend_path: Path) -> int:
        """Generate frontend/Dockerfile"""
        content = """FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
"""
        (frontend_path / "Dockerfile").write_text(content)
        return 1
    
    def _generate_architecture_doc(self, prompt: ProductPrompt, docs_path: Path) -> int:
        """Generate docs/ARCHITECTURE.md"""
        
        # Parse prompt_content
        try:
            content_dict = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            content_dict = {}
        
        arch_desc = content_dict.get('system_architecture', {}).get('architecture_diagram_description', 'Modern SaaS architecture')
        auth_info = json.dumps(content_dict.get('system_architecture', {}).get('authentication', {}), indent=2)
        infra_info = json.dumps(content_dict.get('deployment', {}).get('infrastructure', {}), indent=2)
        
        content = f"""# Architecture - {prompt.idea_name}

## Overview

{arch_desc}

## System Components

### Backend
- Framework: FastAPI
- Database: PostgreSQL
- Cache: Redis

### Frontend
- Framework: Next.js 14
- Language: TypeScript
- Styling: Tailwind CSS

## Authentication

{auth_info}

## Deployment

{infra_info}
"""
        (docs_path / "ARCHITECTURE.md").write_text(content)
        return 1

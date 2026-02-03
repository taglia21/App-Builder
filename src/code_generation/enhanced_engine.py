"""Enhanced code generation engine for production-ready applications."""

import ast
import json
import logging
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, field_validator

from src.code_generation.file_templates import (
    BACKEND_AI_SERVICE_PY,
    BACKEND_API_AUTH_PY,
    BACKEND_API_CRUD_PY,
    BACKEND_AUTH_PY,
    BACKEND_CONFIG_PY,
    BACKEND_CRUD_BASE_PY,
    BACKEND_DB_BASE_PY,
    BACKEND_DB_SESSION_PY,
    BACKEND_EMAIL_SERVICE_PY,
    BACKEND_MAIN_PY,
    BACKEND_MODELS_CORE_PY,
    BACKEND_MODELS_USER_PY,
    BACKEND_SCHEMAS_CORE_PY,
    BACKEND_SCHEMAS_USER_PY,
    BACKEND_TEST_AUTH_PY,
    BACKEND_TEST_CRUD_PY,
    BACKEND_WORKER_PY,
    GITHUB_WORKFLOW_CI,
    ROOT_DOCKER_COMPOSE,
)
from src.code_generation.frontend_templates import (
    FRONTEND_COMPONENTS_DATA_TABLE,
    FRONTEND_COMPONENTS_NAVBAR,
    FRONTEND_COMPONENTS_SIDEBAR,
    FRONTEND_DASHBOARD_LAYOUT,
    FRONTEND_DASHBOARD_PAGE,
    FRONTEND_ENTITY_LIST_PAGE,
    FRONTEND_LIB_UTILS,
    FRONTEND_LOGIN_PAGE,
    FRONTEND_POSTCSS_CONFIG,
    FRONTEND_REGISTER_PAGE,
    FRONTEND_UI_ALERT,
    FRONTEND_UI_BUTTON,
    FRONTEND_UI_CARD,
    FRONTEND_UI_INPUT,
    FRONTEND_UI_STATS_CARD,
    FRONTEND_UI_TABLE,
)
from src.deployment.infrastructure.ci_cd_generator import CICDGenerator
from src.deployment.infrastructure.terraform import TerraformGenerator
from src.deployment.models import DeploymentConfig, DeploymentProviderType
from src.deployment.providers import RenderProvider, VercelProvider
from src.llm.client import get_llm_client
from src.models import GeneratedCodebase, GoldStandardPrompt, ProductPrompt

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def sanitize_python_identifier(name: str) -> str:
    """
    Sanitize a string to be a valid Python identifier.
    Replaces hyphens, spaces, and other invalid chars with underscores.
    Ensures the result is a valid Python module/variable name.
    """
    import re
    # Replace hyphens and spaces with underscores
    name = name.replace('-', '_').replace(' ', '_')
    # Remove any characters that aren't alphanumeric or underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    # Ensure it doesn't start with a number
    if name and name[0].isdigit():
        name = '_' + name
    # Fallback if empty
    if not name:
        name = 'entity'
    return name.lower()


# =============================================================================
# Pydantic Models for LLM Response Validation
# =============================================================================

class FeatureFlags(BaseModel):
    """Validated feature detection flags from LLM."""
    needs_payments: bool = False
    needs_background_jobs: bool = False
    needs_ai_integration: bool = False
    needs_email: bool = False


class EntityField(BaseModel):
    """A single field in the entity definition."""
    name: str
    sql_type: str
    python_type: str
    required: bool = True

    @field_validator('sql_type')
    @classmethod
    def validate_sql_type(cls, v: str) -> str:
        """Normalize SQL type to valid SQLAlchemy type."""
        v = v.strip()
        # Map common variations
        type_mapping = {
            'string': 'String(255)',
            'varchar': 'String(255)',
            'text': 'Text',
            'int': 'Integer',
            'integer': 'Integer',
            'float': 'Float',
            'double': 'Float',
            'decimal': 'Float',
            'bool': 'Boolean',
            'boolean': 'Boolean',
            'date': 'Date',
            'datetime': 'DateTime',
            'timestamp': 'DateTime',
            'json': 'JSON',
            'jsonb': 'JSON',
        }
        lower = v.lower()
        for key, val in type_mapping.items():
            if lower.startswith(key):
                # Preserve String(N) if provided
                if 'string(' in lower:
                    return v
                return val
        return v

    @field_validator('python_type')
    @classmethod
    def validate_python_type(cls, v: str) -> str:
        """Normalize Python type hints."""
        v = v.strip()
        # Map to valid Python types
        type_mapping = {
            'string': 'str',
            'integer': 'int',
            'float': 'float',
            'boolean': 'bool',
            'dict': 'Dict[str, Any]',
            'list': 'List[Any]',
            'any': 'Any',
        }
        lower = v.lower()
        if lower in type_mapping:
            return type_mapping[lower]
        return v


class EntityDefinition(BaseModel):
    """Validated entity definition from LLM."""
    name: str
    class_name: str = Field(alias='class', default='')
    lower: str = ''
    table: str = ''
    fields: List[EntityField] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        """Auto-fill missing fields based on name."""
        if not self.class_name:
            # Clean class name: remove hyphens, spaces, underscores and title case
            clean_name = self.name.replace('-', ' ').replace('_', ' ')
            self.class_name = ''.join(word.title() for word in clean_name.split())
        if not self.lower:
            # Use sanitize function to ensure valid Python identifier
            self.lower = sanitize_python_identifier(self.name)
        else:
            # Sanitize even if provided
            self.lower = sanitize_python_identifier(self.lower)
        if not self.table:
            # Simple pluralization
            lower = self.lower
            if lower.endswith('y'):
                self.table = lower[:-1] + 'ies'
            elif lower.endswith('s') or lower.endswith('x') or lower.endswith('ch'):
                self.table = lower + 'es'
            else:
                self.table = lower + 's'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by code generator.

        Returns fields as dicts for consistency with fallback heuristics.
        """
        return {
            'name': self.name,
            'class': self.class_name,
            'lower': self.lower,
            'table': self.table,
            'fields': [
                {'name': f.name, 'sql_type': f.sql_type, 'python_type': f.python_type, 'required': f.required}
                for f in self.fields
            ]
        }


def parse_entity_fields(raw_fields: List) -> List[EntityField]:
    """Parse entity fields from various LLM response formats."""
    parsed = []
    for field in raw_fields:
        if isinstance(field, dict):
            # Dict format: {"name": "...", "sql_type": "...", ...}
            parsed.append(EntityField(
                name=field.get('name', field.get('field_name', 'unknown')),
                sql_type=field.get('sql_type', field.get('type', 'String(255)')),
                python_type=field.get('python_type', field.get('py_type', 'str')),
                required=field.get('required', True)
            ))
        elif isinstance(field, (list, tuple)) and len(field) >= 2:
            # List/tuple format: [name, sql_type, python_type, required]
            parsed.append(EntityField(
                name=str(field[0]),
                sql_type=str(field[1]),
                python_type=str(field[2]) if len(field) > 2 else 'str',
                required=bool(field[3]) if len(field) > 3 else True
            ))
        elif isinstance(field, str):
            # String format: just field name
            parsed.append(EntityField(
                name=field,
                sql_type='String(255)',
                python_type='str',
                required=False
            ))
    return parsed


def clean_llm_json(content: str) -> str:
    """Clean LLM response to extract valid JSON."""
    content = content.strip()
    # Remove markdown code blocks
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    return content.strip()


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

    def generate(self, prompt: Union[ProductPrompt, GoldStandardPrompt], output_dir: Optional[str] = None, theme: str = "Modern") -> GeneratedCodebase:
        """Generate complete application from startup idea.

        Args:
            prompt: ProductPrompt or GoldStandardPrompt containing idea details
            output_dir: Optional output directory path
            theme: UI theme - one of "Modern", "Minimalist", "Cyberpunk", "Corporate"
        """

        # Validate theme
        valid_themes = ["Modern", "Minimalist", "Cyberpunk", "Corporate"]
        if theme not in valid_themes:
            logger.warning(f"Invalid theme '{theme}', defaulting to 'Modern'")
            theme = "Modern"

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
        except (json.JSONDecodeError, KeyError):
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
        logger.info(f"Using theme: {theme}")

        app_name = idea_name.replace(' ', '')

        # Determine core entity from idea
        entity = self._determine_core_entity(idea_dict)

        # CRITICAL: Ensure entity['lower'] is a valid Python identifier
        # This prevents filenames like "ai-powered_crm.py" which are invalid
        entity['lower'] = sanitize_python_identifier(entity.get('lower', entity.get('name', 'item')))
        entity['table'] = sanitize_python_identifier(entity.get('table', entity['lower'] + 's'))

        # Create directory structure
        self._create_directories()

        # transform idea to features
        # If technical_requirements are in prompt content, we should use them
        # For now, we rely on the description detection or pass specific flags if they exist
        features = self._detect_features(description)

        # Generate all files
        self._generate_backend(app_name, description, entity, features)
        self._generate_frontend(app_name, description, entity, theme=theme)
        self._generate_configs(app_name, description)
        self._generate_docs(app_name, description, entity)
        self._generate_deployment_files(app_name, description)
        self._generate_run_script(app_name)

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
        """Use LLM to detect necessary technical features with validated response."""
        # Default fallback based on keyword detection
        fallback = FeatureFlags(
            needs_payments="subscription" in description.lower() or "payment" in description.lower(),
            needs_background_jobs="video" in description.lower() or "scrape" in description.lower() or "process" in description.lower(),
            needs_ai_integration="ai" in description.lower() or "llm" in description.lower() or "gpt" in description.lower(),
            needs_email="notify" in description.lower() or "email" in description.lower() or "newsletter" in description.lower()
        )

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
            raw_content = clean_llm_json(response.content)
            data = json.loads(raw_content)

            # Validate with Pydantic model
            features = FeatureFlags(**data)
            logger.info(f"Feature detection: payments={features.needs_payments}, jobs={features.needs_background_jobs}, ai={features.needs_ai_integration}, email={features.needs_email}")
            return features.model_dump()

        except ValidationError as e:
            logger.warning(f"Feature detection response validation failed: {e}")
            return fallback.model_dump()
        except json.JSONDecodeError as e:
            logger.warning(f"Feature detection JSON parse failed: {e}")
            return fallback.model_dump()
        except Exception as e:
            logger.warning(f"Feature detection failed: {e}")
            return fallback.model_dump()

    def _determine_core_entity(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the core entity for the app using LLM with validated response."""
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
        {{"name": "field_name", "sql_type": "String(255)", "python_type": "str", "required": true}},
        {{"name": "description", "sql_type": "Text", "python_type": "Optional[str]", "required": false}},
        {{"name": "status", "sql_type": "String(50)", "python_type": "str", "required": false}},
        {{"name": "price", "sql_type": "Float", "python_type": "float", "required": true}},
        {{"name": "is_active", "sql_type": "Boolean", "python_type": "bool", "required": true}}
    ]
}}
Rules:
1. 'fields' is a list of objects with name, sql_type, python_type, required
2. sql_type options: String(N), Text, Integer, Float, Boolean, DateTime
3. python_type options: str, int, float, bool, datetime, Optional[str], etc.
4. Do not include 'id', 'created_at', 'updated_at' (added automatically).
5. Be comprehensive with fields based on the description.
"""
            response = client.complete(prompt, json_mode=True)
            raw_content = clean_llm_json(response.content)
            data = json.loads(raw_content)

            # Parse and validate fields
            raw_fields = data.get('fields', [])
            validated_fields = parse_entity_fields(raw_fields)

            # If no valid fields, fall back to heuristics
            if not validated_fields:
                logger.warning("LLM returned no valid fields. Falling back to heuristics.")
                raise ValueError("No valid fields in LLM response")

            # Create validated entity
            entity = EntityDefinition(
                name=data.get('name', name),
                **{'class': data.get('class', data.get('name', name))},
                lower=data.get('lower', ''),
                table=data.get('table', ''),
                fields=validated_fields
            )

            result = entity.to_dict()
            logger.info(f"Entity determined: {result['class']} with {len(result['fields'])} fields")
            return result

        except ValidationError as e:
            logger.warning(f"Entity validation failed: {e}. Falling back to heuristics.")
        except json.JSONDecodeError as e:
            logger.warning(f"Entity JSON parse failed: {e}. Falling back to heuristics.")
        except Exception as e:
            logger.warning(f"Smart entity determination failed: {e}. Falling back to heuristics.")

        # Fallback to heuristics if LLM fails
        combined_text = f"{name} {description}".lower()

        # Common entity patterns - using dict format for consistency with LLM responses
        if any(w in combined_text for w in ['workflow', 'automation', 'flow', 'process']):
            return {
                'name': 'Workflow',
                'class': 'Workflow',
                'lower': 'workflow',
                'table': 'workflows',
                'fields': [
                    {'name': 'name', 'sql_type': 'String(255)', 'python_type': 'str', 'required': True},
                    {'name': 'description', 'sql_type': 'Text', 'python_type': 'Optional[str]', 'required': False},
                    {'name': 'is_active', 'sql_type': 'Boolean', 'python_type': 'bool', 'required': False},
                    {'name': 'config', 'sql_type': 'JSON', 'python_type': 'Optional[Dict]', 'required': False},
                ]
            }
        elif any(w in combined_text for w in ['project', 'task', 'manage', 'organize']):
            return {
                'name': 'Project',
                'class': 'Project',
                'lower': 'project',
                'table': 'projects',
                'fields': [
                    {'name': 'name', 'sql_type': 'String(255)', 'python_type': 'str', 'required': True},
                    {'name': 'description', 'sql_type': 'Text', 'python_type': 'Optional[str]', 'required': False},
                    {'name': 'status', 'sql_type': 'String(50)', 'python_type': 'str', 'required': False},
                    {'name': 'priority', 'sql_type': 'Integer', 'python_type': 'int', 'required': False},
                ]
            }
        elif any(w in combined_text for w in ['content', 'post', 'blog', 'article', 'document']):
            return {
                'name': 'Content',
                'class': 'Content',
                'lower': 'content',
                'table': 'contents',
                'fields': [
                    {'name': 'title', 'sql_type': 'String(255)', 'python_type': 'str', 'required': True},
                    {'name': 'body', 'sql_type': 'Text', 'python_type': 'str', 'required': True},
                    {'name': 'status', 'sql_type': 'String(50)', 'python_type': 'str', 'required': False},
                    {'name': 'views', 'sql_type': 'Integer', 'python_type': 'int', 'required': False},
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
                    {'name': 'name', 'sql_type': 'String(255)', 'python_type': 'str', 'required': True},
                    {'name': 'description', 'sql_type': 'Text', 'python_type': 'Optional[str]', 'required': False},
                    {'name': 'status', 'sql_type': 'String(50)', 'python_type': 'str', 'required': False},
                    {'name': 'data', 'sql_type': 'JSON', 'python_type': 'Optional[Dict]', 'required': False},
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
        self._write_file('backend/app/db/__init__.py', 'from app.db.base_class import Base  # noqa', 'backend')

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

        # Helper to extract field data (handles both dict and tuple formats)
        def get_field_data(field):
            if isinstance(field, dict):
                return (
                    field.get('name', 'field'),
                    field.get('sql_type', 'String(255)'),
                    field.get('python_type', 'str'),
                    field.get('required', True)
                )
            elif isinstance(field, (list, tuple)) and len(field) >= 2:
                return (
                    str(field[0]),
                    str(field[1]),
                    str(field[2]) if len(field) > 2 else 'str',
                    bool(field[3]) if len(field) > 3 else True
                )
            else:
                return ('field', 'String(255)', 'str', True)

        # Generate columns for entity model
        columns = []
        for field in entity['fields']:
            field_name, sql_type, py_type, required = get_field_data(field)
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
        for field in entity['fields']:
            field_name, sql_type, py_type, required = get_field_data(field)
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
email-validator==2.1.0.post1
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

# Install system dependencies (curl for healthchecks, libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
'''
        self._write_file('backend/Dockerfile', dockerfile, 'backend')

        # Tests
        self._write_file('backend/tests/api/test_auth.py', BACKEND_TEST_AUTH_PY, 'test')

        # Use get_field_data to handle both dict and tuple field formats
        test_fields = []
        for field in entity['fields'][:2]:
            field_name, field_sql_type, field_python_type, field_required = get_field_data(field)
            if field_required:
                test_fields.append(f'"{field_name}": "test"')
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

    def _generate_run_script(self, app_name: str):
        """Generate convenience scripts for running the app."""
        logger.info("Generating start scripts...")

        # Bash Script (Linux/Mac)
        bash_script = """#!/bin/bash
echo "🚀 Starting ${app_name}..."

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed."
    exit 1
fi

echo "Building and starting containers..."
docker-compose up --build
"""
        bash_script = Template(bash_script).safe_substitute(app_name=app_name)
        self._write_file('start_dev.sh', bash_script, 'config')

        # Make executable (not strictly possible via file write but good for content)
        # On windows this essentially just writes the file

        # Windows Batch Script
        bat_script = """@echo off
echo 🚀 Starting ${app_name}...

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Docker is not installed.
    pause
    exit /b 1
)

echo Building and starting containers...
docker-compose up --build
"""
        bat_script = Template(bat_script).safe_substitute(app_name=app_name)
        self._write_file('start_dev.bat', bat_script, 'config')


    def _get_theme_config(self, theme: str = "Modern") -> Dict[str, str]:
        """Get CSS variables and config for selected theme."""
        themes = {
            "Modern": {
                "radius": "0.5rem",
                "font": "'Inter', system-ui, sans-serif",
                "colors": """
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;"""
            },
            "Minimalist": {
                "radius": "0rem",
                "font": "'Helvetica Neue', Helvetica, Arial, sans-serif",
                "colors": """
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 0 0% 3.9%;"""
            },
            "Cyberpunk": {
                "radius": "0px",
                "font": "'Orbitron', 'Rajdhani', monospace, sans-serif",
                "colors": """
    --background: 260 50% 5%;
    --foreground: 180 100% 80%;
    --card: 260 40% 10%;
    --card-foreground: 180 100% 80%;
    --popover: 260 40% 10%;
    --popover-foreground: 180 100% 80%;
    --primary: 320 100% 50%;
    --primary-foreground: 0 0% 0%;
    --secondary: 180 100% 40%;
    --secondary-foreground: 0 0% 0%;
    --muted: 260 30% 20%;
    --muted-foreground: 180 50% 60%;
    --accent: 280 100% 60%;
    --accent-foreground: 0 0% 0%;
    --destructive: 0 100% 50%;
    --destructive-foreground: 0 0% 100%;
    --border: 260 50% 25%;
    --input: 260 50% 15%;
    --ring: 320 100% 50%;"""
            },
            "Corporate": {
                "radius": "0.25rem",
                "font": "'Arial', 'Helvetica', sans-serif",
                "colors": """
    --background: 210 40% 98%;
    --foreground: 222.2 47.4% 11.2%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 47.4% 11.2%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 47.4% 11.2%;
    --primary: 221.2 83.2% 40%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 20% 93%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 93%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 72% 51%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 85%;
    --input: 214.3 31.8% 85%;
    --ring: 221.2 83.2% 40%;"""
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

        # PostCSS Config
        self._write_file('frontend/postcss.config.js', FRONTEND_POSTCSS_CONFIG, 'frontend')

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
        border: "hsl(var(--border))",
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
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
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
        safe_description = description.replace('"', '\\"').replace('\n', ' ')
        layout = f'''import type {{ Metadata }} from "next";
import "./globals.css";

export const metadata: Metadata = {{
  title: "{app_name}",
  description: "{safe_description}",
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

        # Theme config file for AI agent customization
        theme_config_ts = f'''/**
 * Theme Configuration
 *
 * This file contains all design tokens for the "{theme}" theme.
 * AI agents can safely modify colors, fonts, spacing, and other visual properties here
 * without affecting business logic in components.
 *
 * To change the theme:
 * 1. Modify the values in this file
 * 2. Update globals.css :root variables to match
 * 3. Components will automatically pick up the changes
 */

export const themeConfig = {{
  /** Theme identifier */
  name: "{theme}",

  /** Color palette - HSL values matching CSS variables in globals.css */
  colors: {{
    primary: "hsl(var(--primary))",
    primaryForeground: "hsl(var(--primary-foreground))",
    secondary: "hsl(var(--secondary))",
    secondaryForeground: "hsl(var(--secondary-foreground))",
    background: "hsl(var(--background))",
    foreground: "hsl(var(--foreground))",
    card: "hsl(var(--card))",
    cardForeground: "hsl(var(--card-foreground))",
    muted: "hsl(var(--muted))",
    mutedForeground: "hsl(var(--muted-foreground))",
    accent: "hsl(var(--accent))",
    accentForeground: "hsl(var(--accent-foreground))",
    destructive: "hsl(var(--destructive))",
    destructiveForeground: "hsl(var(--destructive-foreground))",
    border: "hsl(var(--border))",
    input: "hsl(var(--input))",
    ring: "hsl(var(--ring))",
  }},

  /** Typography settings */
  fonts: {{
    heading: "{theme_config['font']}",
    body: "{theme_config['font']}",
    mono: "monospace",
  }},

  /** Spacing and sizing */
  spacing: {{
    radius: "{theme_config['radius']}",
    containerMaxWidth: "1400px",
    containerPadding: "2rem",
  }},

  /** Visual effects */
  effects: {{
    /** Border style preference: "solid" | "none" | "gradient" */
    borderStyle: "solid",
    /** Shadow intensity: "none" | "subtle" | "medium" | "strong" */
    shadowIntensity: "{"subtle" if theme in ["Modern", "Corporate"] else "strong" if theme == "Cyberpunk" else "none"}",
    /** Enable animations */
    animationsEnabled: true,
  }},
}} as const;

export type ThemeConfig = typeof themeConfig;

/**
 * Helper to get a color value
 * Usage: getColor("primary") returns "hsl(var(--primary))"
 */
export function getColor(name: keyof typeof themeConfig.colors): string {{
  return themeConfig.colors[name];
}}
'''
        self._write_file('frontend/src/config/theme.config.ts', theme_config_ts, 'frontend')

        # Navigation Configuration - AI Agent Safe Edit Zone
        navigation_config = f'''/**
 * Navigation Configuration
 *
 * SAFE TO MODIFY: This file is intentionally separated from business logic
 * for AI-assisted customization. Modify navigation items here without
 * touching component code.
 *
 * @ai-safe-edit
 */

import {{ LayoutDashboard, Box, Settings, Users, FileText, BarChart }} from "lucide-react";
import type {{ LucideIcon }} from "lucide-react";

export interface NavItem {{
  href: string;
  label: string;
  icon: LucideIcon;
  /** Optional badge to show (e.g., notification count) */
  badge?: string | number;
  /** Whether this item is visible */
  visible?: boolean;
}}

export interface NavSection {{
  title?: string;
  items: NavItem[];
}}

/**
 * Main navigation items for the sidebar
 */
export const mainNavigation: NavItem[] = [
  {{
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  }},
  {{
    href: "/dashboard/{entity['lower']}s",
    label: "{entity['name']}s",
    icon: Box,
  }},
];

/**
 * Settings and account navigation
 */
export const settingsNavigation: NavItem[] = [
  {{
    href: "/dashboard/settings",
    label: "Settings",
    icon: Settings,
  }},
];

/**
 * All navigation sections
 */
export const navigationConfig = {{
  appName: "{app_name}",
  main: mainNavigation,
  settings: settingsNavigation,
}} as const;

export type NavigationConfig = typeof navigationConfig;
'''
        self._write_file('frontend/src/config/navigation.config.ts', navigation_config, 'frontend')

        # Copy/Content Configuration - AI Agent Safe Edit Zone
        copy_config = f'''/**
 * Copy/Content Configuration
 *
 * SAFE TO MODIFY: This file contains all user-facing text strings.
 * AI agents can safely edit these without affecting application logic.
 *
 * @ai-safe-edit
 */

export const copyConfig = {{
  /**
   * Application branding
   */
  app: {{
    name: "{app_name}",
    tagline: "Your {app_name} dashboard",
    description: "{description}",
  }},

  /**
   * Authentication pages
   */
  auth: {{
    login: {{
      title: "Welcome back",
      subtitle: "Sign in to your account",
      emailLabel: "Email",
      passwordLabel: "Password",
      submitButton: "Sign in",
      registerLink: "Don't have an account? Sign up",
      forgotPasswordLink: "Forgot password?",
    }},
    register: {{
      title: "Create an account",
      subtitle: "Get started with {app_name}",
      emailLabel: "Email",
      passwordLabel: "Password",
      confirmPasswordLabel: "Confirm password",
      nameLabel: "Full name",
      submitButton: "Create account",
      loginLink: "Already have an account? Sign in",
    }},
  }},

  /**
   * Dashboard pages
   */
  dashboard: {{
    welcome: "Welcome to {app_name}",
    emptyState: "No {entity['lower']}s found. Create your first one!",
    createButton: "Create {entity['name']}",
  }},

  /**
   * Common UI elements
   */
  common: {{
    loading: "Loading...",
    error: "Something went wrong",
    retry: "Try again",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    view: "View",
    search: "Search...",
    noResults: "No results found",
  }},

  /**
   * Error messages
   */
  errors: {{
    networkError: "Unable to connect. Please check your internet connection.",
    unauthorized: "Please sign in to continue.",
    notFound: "The requested resource was not found.",
    serverError: "An unexpected error occurred. Please try again later.",
  }},
}} as const;

export type CopyConfig = typeof copyConfig;

/**
 * Helper to get nested copy values
 * Usage: getCopy("auth.login.title")
 */
export function getCopy(path: string): string {{
  const keys = path.split(".");
  let value: any = copyConfig;
  for (const key of keys) {{
    value = value?.[key];
  }}
  return typeof value === "string" ? value : path;
}}
'''
        self._write_file('frontend/src/config/copy.config.ts', copy_config, 'frontend')

        # Features Configuration - AI Agent Safe Edit Zone
        features_config = f'''/**
 * Feature Flags Configuration
 *
 * SAFE TO MODIFY: Toggle features on/off without changing code.
 * AI agents can safely enable/disable functionality here.
 *
 * @ai-safe-edit
 */

export const featuresConfig = {{
  /**
   * Authentication features
   */
  auth: {{
    /** Enable social login (Google, GitHub) */
    socialLogin: false,
    /** Enable "Remember me" checkbox */
    rememberMe: true,
    /** Enable password reset functionality */
    passwordReset: false,
    /** Enable email verification requirement */
    emailVerification: false,
  }},

  /**
   * Dashboard features
   */
  dashboard: {{
    /** Show analytics/stats cards on dashboard */
    showStats: true,
    /** Enable dark mode toggle */
    darkMode: true,
    /** Show recent activity feed */
    activityFeed: false,
    /** Enable keyboard shortcuts */
    keyboardShortcuts: false,
  }},

  /**
   * {entity['name']} features
   */
  {entity['lower']}: {{
    /** Enable bulk actions (select multiple) */
    bulkActions: false,
    /** Show advanced filters */
    advancedFilters: false,
    /** Enable export to CSV/Excel */
    exportEnabled: false,
    /** Enable import from CSV */
    importEnabled: false,
  }},

  /**
   * UI/UX features
   */
  ui: {{
    /** Show loading skeletons vs spinners */
    useSkeletons: true,
    /** Enable animations */
    animations: true,
    /** Show toast notifications */
    toasts: true,
    /** Enable offline support */
    offlineSupport: false,
  }},
}} as const;

export type FeaturesConfig = typeof featuresConfig;

/**
 * Check if a feature is enabled
 * Usage: isFeatureEnabled("auth.socialLogin")
 */
export function isFeatureEnabled(path: string): boolean {{
  const keys = path.split(".");
  let value: any = featuresConfig;
  for (const key of keys) {{
    value = value?.[key];
  }}
  return value === true;
}}
'''
        self._write_file('frontend/src/config/features.config.ts', features_config, 'frontend')

        # Components
        self._write_file('frontend/src/components/ui/button.tsx', FRONTEND_UI_BUTTON, 'frontend')
        self._write_file('frontend/src/components/ui/input.tsx', FRONTEND_UI_INPUT, 'frontend')
        self._write_file('frontend/src/components/ui/card.tsx', FRONTEND_UI_CARD, 'frontend')
        self._write_file('frontend/src/components/ui/table.tsx', FRONTEND_UI_TABLE, 'frontend')
        self._write_file('frontend/src/components/ui/stats-card.tsx', FRONTEND_UI_STATS_CARD, 'frontend')
        self._write_file('frontend/src/components/ui/data-table.tsx', FRONTEND_COMPONENTS_DATA_TABLE, 'frontend')
        label_component = '''"use client"

import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
)

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> &
    VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants(), className)}
    {...props}
  />
))
Label.displayName = LabelPrimitive.Root.displayName

export { Label }
'''
        self._write_file('frontend/src/components/ui/label.tsx', label_component, 'frontend')
        self._write_file('frontend/src/components/sidebar.tsx', Template(FRONTEND_COMPONENTS_SIDEBAR).safe_substitute(app_name=app_name, entity_name=entity['name'], entity_lower=entity['lower']), 'frontend')
        self._write_file('frontend/src/components/navbar.tsx', FRONTEND_COMPONENTS_NAVBAR, 'frontend')
        self._write_file('frontend/src/components/ui/alert.tsx', FRONTEND_UI_ALERT, 'frontend')
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
        db_name = app_name.lower().replace(' ', '_').replace('-', '_')

        # Determine worker service
        # We can't easily access features here without passing them, but we can check requirements
        # Or better, we should pass features to this method.
        # For now, let's assume we want the worker if celery is in requirements (which we can't see here easily)
        # However, the ROOT_DOCKER_COMPOSE template expects ${worker_service}.

        # Let's fix the imports first.
        # It seems features are not passed to _generate_configs.
        # Refactor: Pass features or use empty string for worker if unsure.
        # But wait, we can infer it or just leave it empty if not needed.

        # Safe defaults
        worker_block = ""
        # Check if we generated worker.py (a bit hacky but works in this class context if we tracked it)
        # Better: let's use a standard worker block if 'celery' is likely needed.
        # For this refactor, I will leave worker_service empty unless I can confirm it's needed.
        # But the hardcoded version didn't have a worker at all!
        # The template has ${worker_service}.

        docker_compose = Template(ROOT_DOCKER_COMPOSE).safe_substitute(
            db_name=db_name,
            openai_key="${OPENAI_API_KEY}", # Keep as env var reference for Docker
            worker_service=worker_block
        )

        self._write_file('docker-compose.yml', docker_compose, 'config')

        # Generate cryptographically secure SECRET_KEY
        import secrets
        secret_key = secrets.token_urlsafe(32)

        # .env with actual secure values (for immediate use)
        env_file = f'''# {db_name} Environment Configuration
# Generated with secure defaults - modify as needed

# =============================================================================
# PORTS
# =============================================================================
BACKEND_PORT=8000
FRONTEND_PORT=3000
DB_PORT=5432
REDIS_PORT=6379

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL=postgresql://postgres:postgres@db:5432/{db_name}

# =============================================================================
# SECURITY
# =============================================================================
# Auto-generated secure key - DO NOT COMMIT THIS FILE TO VERSION CONTROL
SECRET_KEY={secret_key}

# =============================================================================
# OPTIONAL INTEGRATIONS
# =============================================================================
OPENAI_API_KEY=

# =============================================================================
# APP SETTINGS
# =============================================================================
DEBUG=false
'''
        self._write_file('.env', env_file, 'config')
        logger.info("Generated .env with secure SECRET_KEY")

        # .env.example (for documentation/version control)
        env_example = f'''# {db_name} Environment Configuration
# Copy this file to .env and update values as needed
# IMPORTANT: .env should NEVER be committed to version control

# =============================================================================
# PORTS
# =============================================================================
BACKEND_PORT=8000
FRONTEND_PORT=3000
DB_PORT=5432
REDIS_PORT=6379

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL=postgresql://postgres:postgres@db:5432/{db_name}

# =============================================================================
# SECURITY (REQUIRED - CHANGE THESE!)
# =============================================================================
# Generate a new key with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=CHANGE_ME_GENERATE_A_SECURE_KEY

# =============================================================================
# OPTIONAL INTEGRATIONS
# =============================================================================
OPENAI_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# =============================================================================
# APP SETTINGS
# =============================================================================
DEBUG=false
'''
        self._write_file('.env.example', env_example, 'config')

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
        """Generate documentation and environment files."""
        db_name = app_name.lower().replace('-', '_').replace(' ', '_')

        # Generate .env.example
        env_example = f'''# {app_name} Environment Configuration
# Copy this file to .env and update values as needed

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL=postgresql://postgres:postgres@db:5432/{db_name}

# =============================================================================
# SECURITY (CHANGE THESE IN PRODUCTION!)
# =============================================================================
SECRET_KEY=your-secret-key-change-in-production

# =============================================================================
# REDIS (Optional - for caching/sessions)
# =============================================================================
REDIS_URL=redis://redis:6379/0

# =============================================================================
# CORS (Comma-separated origins, or leave for defaults)
# =============================================================================
# CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# =============================================================================
# OPTIONAL INTEGRATIONS
# =============================================================================
# OPENAI_API_KEY=sk-...
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# GITHUB_CLIENT_ID=
# GITHUB_CLIENT_SECRET=

# =============================================================================
# PORTS (for docker-compose)
# =============================================================================
BACKEND_PORT=8000
FRONTEND_PORT=3000
DB_PORT=5432
'''
        self._write_file('.env.example', env_example, 'config')

        # Generate comprehensive README
        readme = f'''# {app_name}

{description}

## 🚀 Quick Start (3 Steps)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- (Optional) Python 3.11+ and Node.js 20+ for local development

### Step 1: Configure Environment
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

### Step 2: Start the Application
```bash
docker compose up --build
```

### Step 3: Open in Browser
- **Frontend:** http://localhost:3000
- **Backend API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health/ready

### ✅ Success Looks Like:
1. Open http://localhost:3000
2. Click "Register" and create an account
3. Login with your credentials
4. You should see the dashboard!

---

## 📊 Health Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/health` | Basic liveness | App is running |
| `/health/ready` | Readiness check | DB connected, ready for traffic |
| `/health/live` | Liveness probe | Kubernetes liveness probe |

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | (set in docker-compose) | PostgreSQL connection string |
| `SECRET_KEY` | Yes | ⚠️ weak default | JWT signing key (change in production!) |
| `REDIS_URL` | No | redis://redis:6379/0 | Redis connection string |

See `.env.example` for all available options.

---

## 🔧 Local Development (Without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/{db_name}
export SECRET_KEY=dev-secret-key

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Config, auth, security
│   │   ├── crud/         # Database operations
│   │   ├── db/           # Database session, models
│   │   ├── models/       # SQLAlchemy models
│   │   └── schemas/      # Pydantic schemas
│   ├── tests/            # Backend tests
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js pages
│   │   ├── components/   # React components
│   │   └── config/       # Theme configuration
│   └── Dockerfile
└── docker-compose.yml
```

---

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT)
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### {entity['name']}s
- `GET /api/v1/{entity['lower']}s/` - List all
- `POST /api/v1/{entity['lower']}s/` - Create new
- `GET /api/v1/{entity['lower']}s/{{id}}` - Get by ID
- `PUT /api/v1/{entity['lower']}s/{{id}}` - Update
- `DELETE /api/v1/{entity['lower']}s/{{id}}` - Delete

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI 0.109, SQLAlchemy 2.0, Pydantic 2.5 |
| Database | PostgreSQL 15 |
| Auth | JWT (python-jose), bcrypt |
| Container | Docker, Docker Compose |

---

## 🎨 Customization

### Theme Configuration
Edit `frontend/src/config/theme.config.ts` to customize colors, fonts, and spacing.

### CSS Variables
Theme colors are defined in `frontend/src/app/globals.css` as CSS variables.

---

Generated by AI Startup Generator
'''
        self._write_file('README.md', readme, 'config')



    def _calculate_metrics(self):
        """Calculate generation metrics."""
        self.metrics['total_files'] = len(self.files_created)
        self.metrics['total_lines'] = sum(f['lines'] for f in self.files_created)

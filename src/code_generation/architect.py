"""
Intelligent Architecture Designer for Ignara.

Takes a plain-English idea and produces a complete system specification
using multiple LLM calls to decompose the problem:

1. Entity Extraction — identify all business objects, their fields, and relationships
2. API Design — design RESTful endpoints with business logic descriptions
3. Page/UI Design — plan frontend pages and their components
4. Permission Model — define roles and access control
5. Integration Detection — identify needed third-party services

This replaces the old single-entity detection with a full system design.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Spec Models
# =============================================================================


class FieldSpec(BaseModel):
    """Specification for a single entity field."""

    name: str
    type: str = "string"
    required: bool = True
    description: str = ""
    default: Optional[str] = None
    validation_rules: List[str] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize field type to a consistent set."""
        mapping = {
            "str": "string",
            "int": "integer",
            "float": "decimal",
            "bool": "boolean",
            "datetime": "timestamp",
            "date": "date",
            "dict": "object",
            "list": "array",
            "text": "text",
            "uuid": "uuid",
            "json": "object",
            "jsonb": "object",
            "varchar": "string",
        }
        normalized = v.strip().lower()
        # Handle parameterized types like String(255)
        base = re.split(r"[\(\[]", normalized)[0].strip()
        return mapping.get(base, v.strip().lower())


class RelationshipSpec(BaseModel):
    """A relationship between two entities."""

    entity: str
    type: str = "many-to-one"  # one-to-one, one-to-many, many-to-one, many-to-many
    description: str = ""
    foreign_key: Optional[str] = None
    through_table: Optional[str] = None  # for many-to-many

    @field_validator("type")
    @classmethod
    def normalize_relationship_type(cls, v: str) -> str:
        valid = {"one-to-one", "one-to-many", "many-to-one", "many-to-many"}
        normalized = v.strip().lower().replace("_", "-").replace(" ", "-")
        if normalized not in valid:
            logger.warning(f"Unknown relationship type '{v}', defaulting to 'many-to-one'")
            return "many-to-one"
        return normalized


class EntitySpec(BaseModel):
    """Specification for a business entity / database model."""

    name: str
    plural: str = ""
    description: str = ""
    fields: List[FieldSpec] = Field(default_factory=list)
    relationships: List[RelationshipSpec] = Field(default_factory=list)
    soft_delete: bool = True
    timestamps: bool = True  # created_at / updated_at
    indexes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_plural(self) -> "EntitySpec":
        if not self.plural:
            name_lower = self.name.lower()
            if name_lower.endswith("y"):
                self.plural = name_lower[:-1] + "ies"
            elif name_lower.endswith(("s", "x", "ch", "sh")):
                self.plural = name_lower + "es"
            else:
                self.plural = name_lower + "s"
        return self


class SchemaSpec(BaseModel):
    """Request or response schema for an API route."""

    fields: Dict[str, str] = Field(default_factory=dict)
    example: Optional[Dict[str, Any]] = None


class RouteSpec(BaseModel):
    """Specification for a single API endpoint."""

    path: str
    method: str = "GET"
    summary: str = ""
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    auth_required: bool = True
    request_schema: Optional[SchemaSpec] = None
    response_schema: Optional[SchemaSpec] = None
    business_logic: str = ""
    status_codes: Dict[str, str] = Field(default_factory=dict)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        return v.strip().upper()


class ComponentSpec(BaseModel):
    """A UI component within a page."""

    name: str
    type: str = "generic"  # e.g., table, form, chart, card, modal
    description: str = ""
    data_source: Optional[str] = None


class PageSpec(BaseModel):
    """Specification for a frontend page."""

    route: str
    title: str
    description: str = ""
    layout_type: str = "default"  # default, auth, dashboard, full-width, split
    auth_required: bool = True
    components: List[ComponentSpec] = Field(default_factory=list)
    related_entities: List[str] = Field(default_factory=list)


class RoleSpec(BaseModel):
    """Specification for a user role and its permissions."""

    name: str
    description: str = ""
    permissions: List[str] = Field(default_factory=list)
    is_default: bool = False
    inherits_from: Optional[str] = None


class IntegrationSpec(BaseModel):
    """Specification for a third-party service integration."""

    name: str
    purpose: str
    category: str = "other"  # payment, email, storage, auth, analytics, communication, ai, other
    required: bool = False
    env_vars: List[str] = Field(default_factory=list)


class TechStackSpec(BaseModel):
    """Technology stack specification."""

    backend_framework: str = "FastAPI"
    backend_language: str = "Python 3.11+"
    frontend_framework: str = "Next.js 14"
    frontend_language: str = "TypeScript"
    styling: str = "Tailwind CSS"
    database: str = "PostgreSQL"
    cache: str = "Redis"
    task_queue: Optional[str] = None
    search_engine: Optional[str] = None
    object_storage: Optional[str] = None
    containerization: str = "Docker"
    ci_cd: str = "GitHub Actions"
    hosting: str = "AWS"
    orm: str = "SQLAlchemy"
    auth_method: str = "JWT"
    api_style: str = "REST"
    testing: str = "pytest + Jest"


class SystemSpec(BaseModel):
    """
    Complete system specification for an application.

    Produced by SystemArchitect from a plain-English idea description.
    """

    app_name: str
    description: str
    entities: List[EntitySpec] = Field(default_factory=list)
    api_routes: List[RouteSpec] = Field(default_factory=list)
    pages: List[PageSpec] = Field(default_factory=list)
    roles: List[RoleSpec] = Field(default_factory=list)
    integrations: List[IntegrationSpec] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)
    tech_stack: TechStackSpec = Field(default_factory=TechStackSpec)
    features: List[str] = Field(default_factory=list)

    # Sprint 6: Enhanced architect fields
    # Recommended library versions for the tech stack (e.g., "React 18.2", "FastAPI 0.109")
    tech_stack_recommendation: List[str] = Field(
        default_factory=list,
        description="Recommended specific library versions (e.g., 'React 18.2', 'FastAPI 0.109', 'PostgreSQL 16')",
    )
    # Directory layout tree for the generated project
    project_structure: Optional[str] = Field(
        default=None,
        description="Directory layout tree string describing the project file structure",
    )
    # API endpoint design with method, path, and description
    api_design: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of API endpoints with method, path, and description fields",
    )

    # Metadata populated by the architect
    architect_version: str = "2.0"
    llm_steps_completed: List[str] = Field(default_factory=list)
    generation_time_ms: float = 0.0


# =============================================================================
# JSON Parsing Utilities
# =============================================================================


def clean_llm_json(content: str) -> str:
    """
    Strip markdown code fences and whitespace from an LLM JSON response.

    Handles patterns like:
      ```json\\n{...}\\n```
      ```\\n{...}\\n```
      {...}
    """
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def safe_parse_json(content: str, step_name: str = "unknown") -> Optional[Dict[str, Any]]:
    """
    Attempt to parse JSON from an LLM response with multiple fallback strategies.

    Strategies (in order):
    1. Direct json.loads after clean_llm_json
    2. Regex extraction of first {...} block
    3. Regex extraction of first [...] block (for array responses)

    Returns:
        Parsed dict/list or None if all strategies fail.
    """
    # Strategy 1: Clean and parse
    cleaned = clean_llm_json(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"[{step_name}] Direct JSON parse failed: {e}")

    # Strategy 2: Extract first JSON object
    obj_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError as e:
            logger.debug(f"[{step_name}] Object extraction failed: {e}")

    # Strategy 3: Extract first JSON array
    arr_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError as e:
            logger.debug(f"[{step_name}] Array extraction failed: {e}")

    logger.warning(f"[{step_name}] All JSON parse strategies failed. Raw length={len(content)}")
    return None


# =============================================================================
# System Architect
# =============================================================================


class SystemArchitect:
    """
    Intelligent Architecture Designer.

    Orchestrates a multi-step LLM pipeline to transform a plain-English
    idea description into a comprehensive SystemSpec covering:
    - Data entities and relationships
    - RESTful API routes with business logic
    - Frontend pages and components
    - Role-based permissions
    - Third-party integrations
    - Business rules and tech stack

    Usage::

        architect = SystemArchitect()
        spec = await architect.design(
            idea_name="TalentBoard",
            idea_description="A hiring platform for remote teams...",
            features=["job postings", "applicant tracking", "video interviews"],
        )
    """

    # -------------------------------------------------------------------------
    # Initialisation
    # -------------------------------------------------------------------------

    def __init__(self, llm_client=None, provider: str = "auto"):
        """
        Initialise the SystemArchitect.

        Args:
            llm_client: An existing BaseLLMClient instance.  If None, one is
                        created automatically via get_llm_client(provider).
            provider:   Provider string passed to get_llm_client when
                        llm_client is not supplied.  Defaults to "auto".
        """
        if llm_client is not None:
            self._client = llm_client
        else:
            # Deferred import to avoid circular imports at module load time
            from src.llm.client import get_llm_client  # noqa: PLC0415
            self._client = get_llm_client(provider)
            logger.info(
                f"SystemArchitect initialised with provider={provider!r}, "
                f"model={self._client.model!r}"
            )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def design(
        self,
        idea_name: str,
        idea_description: str,
        features: Optional[List[str]] = None,
        customization: Optional[Dict[str, Any]] = None,
    ) -> SystemSpec:
        """
        Orchestrate a multi-step LLM pipeline to produce a full SystemSpec.

        Steps:
          1. High-level decomposition — what this app is and its core features
          2. Entity / data-model design — entities with fields and relationships
          3. API routes design — RESTful endpoints with business logic
          4. Frontend pages and components
          5. Validation / consistency check — permissions, integrations, rules

        Args:
            idea_name:        Short name for the application.
            idea_description: Plain-English description of the idea.
            features:         Optional list of feature strings to guide the LLM.

        Returns:
            A fully populated SystemSpec instance.
        """
        t0 = time.time()
        features = features or []
        steps_completed: List[str] = []

        logger.info(f"SystemArchitect.design → '{idea_name}' ({len(idea_description)} chars)")

        # Build a shared context string reused across prompts
        context = self._build_context(idea_name, idea_description, features)

        if customization:
            context += "\n\nCustomization preferences:\n"
            context += f"- Backend framework: {customization.get('backend_framework', 'fastapi')}\n"
            context += f"- Database: {customization.get('database', 'postgresql')}\n"
            context += f"- Auth strategy: {customization.get('auth_strategy', 'jwt')}\n"
            context += f"- Frontend framework: {customization.get('frontend_framework', 'nextjs')}\n"
            context += f"- CSS framework: {customization.get('css_framework', 'tailwind')}\n"
            context += f"- Deployment target: {customization.get('deployment_target', 'docker')}\n"
            context += f"- API style: {customization.get('api_style', 'rest')}\n"
            if customization.get('extra_instructions'):
                context += f"- Extra instructions: {customization['extra_instructions']}\n"

        # ---------- Step 1: High-level decomposition ----------
        decomposition: Dict[str, Any] = {}
        try:
            decomposition = await asyncio.to_thread(
                self._step1_decompose, context, idea_name
            )
            steps_completed.append("decomposition")
            logger.info("Step 1 (decomposition) complete")
        except Exception as exc:
            logger.warning(f"Step 1 failed: {exc}")

        # Merge features from decomposition into the feature list
        detected_features: List[str] = decomposition.get("features", features)

        # ---------- Step 2: Entity / data model ----------
        entities: List[EntitySpec] = []
        try:
            entities = await asyncio.to_thread(
                self._step2_entities, context, decomposition
            )
            steps_completed.append("entities")
            logger.info(f"Step 2 (entities) complete → {len(entities)} entities")
        except Exception as exc:
            logger.warning(f"Step 2 failed: {exc}")

        # ---------- Step 3: API routes ----------
        routes: List[RouteSpec] = []
        try:
            routes = await asyncio.to_thread(
                self._step3_routes, context, entities, decomposition
            )
            steps_completed.append("routes")
            logger.info(f"Step 3 (routes) complete → {len(routes)} routes")
        except Exception as exc:
            logger.warning(f"Step 3 failed: {exc}")

        # ---------- Step 4: Frontend pages ----------
        pages: List[PageSpec] = []
        try:
            pages = await asyncio.to_thread(
                self._step4_pages, context, entities, decomposition
            )
            steps_completed.append("pages")
            logger.info(f"Step 4 (pages) complete → {len(pages)} pages")
        except Exception as exc:
            logger.warning(f"Step 4 failed: {exc}")

        # ---------- Step 5: Permissions, integrations, rules, tech stack ----------
        cross_cutting: Dict[str, Any] = {}
        try:
            cross_cutting = await asyncio.to_thread(
                self._step5_cross_cutting, context, entities, decomposition
            )
            steps_completed.append("cross_cutting")
            logger.info("Step 5 (cross-cutting) complete")
        except Exception as exc:
            logger.warning(f"Step 5 failed: {exc}")

        # ---------- Assemble the SystemSpec ----------
        spec = self._assemble_spec(
            idea_name=idea_name,
            idea_description=idea_description,
            decomposition=decomposition,
            entities=entities,
            routes=routes,
            pages=pages,
            cross_cutting=cross_cutting,
            features=detected_features,
            steps_completed=steps_completed,
        )

        spec.generation_time_ms = (time.time() - t0) * 1000
        logger.info(
            f"SystemArchitect finished '{idea_name}' in {spec.generation_time_ms:.0f}ms "
            f"| steps={steps_completed} | entities={len(spec.entities)} "
            f"| routes={len(spec.api_routes)} | pages={len(spec.pages)}"
        )
        return spec

    # -------------------------------------------------------------------------
    # Private: Context Builder
    # -------------------------------------------------------------------------

    def _build_context(
        self,
        idea_name: str,
        idea_description: str,
        features: List[str],
    ) -> str:
        """Return a compact context block reused in every prompt."""
        feature_block = ""
        if features:
            feature_block = "Key features requested:\n" + "\n".join(f"  - {f}" for f in features)
        return f"""App Name: {idea_name}
Description: {idea_description}
{feature_block}""".strip()

    # -------------------------------------------------------------------------
    # Private: Step 1 — High-level decomposition
    # -------------------------------------------------------------------------

    def _step1_decompose(
        self,
        context: str,
        idea_name: str,
    ) -> Dict[str, Any]:
        """
        Ask the LLM to decompose the idea into top-level concepts.

        Returns dict with keys: summary, core_features, target_users,
        tech_stack_hints, complexity_estimate.
        """
        system_prompt = (
            "You are a world-class software architect who has designed systems at Google, Stripe, and Vercel. "
            "Your task is to analyse a startup idea and produce a thorough, investor-grade system decomposition. "
            "Think deeply about edge cases, scalability, and what would make this a production-ready SaaS. "
            "Be thorough, practical, and realistic. Return only valid JSON."
        )
        prompt = f"""{context}

Produce a high-level decomposition of this application.

Return a JSON object with this exact structure:
{{
  "summary": "One-paragraph summary of what the app does and who it serves.",
  "core_features": ["feature 1", "feature 2", "..."],
  "target_users": ["user type 1", "user type 2"],
  "user_roles": ["admin", "member", "..."],
  "tech_stack_hints": {{
    "needs_payments": true,
    "needs_email_notifications": false,
    "needs_file_storage": false,
    "needs_search": false,
    "needs_realtime": false,
    "needs_ai": false,
    "needs_background_jobs": false
  }},
  "business_rules": [
    "Rule 1: plain English description",
    "Rule 2: ..."
  ],
  "complexity_estimate": "low | medium | high",
  "monetization_model": "Description of how this app can generate revenue",
  "scaling_considerations": ["consideration 1", "consideration 2"],
  "security_requirements": ["requirement 1", "requirement 2"],
  "third_party_integrations": ["Stripe for payments", "SendGrid for emails", "..."]
}}

Focus on what this specific app needs — do not add generic features."""

        response = self._client.complete(
            prompt,
            system_prompt=system_prompt,
            max_tokens=2048,
            temperature=0.4,
            json_mode=True,
        )
        data = safe_parse_json(response.content, step_name="step1_decompose")
        if data is None:
            logger.warning("Step 1: could not parse JSON, returning empty decomposition")
            return {}
        return data

    # -------------------------------------------------------------------------
    # Private: Step 2 — Entity / data model
    # -------------------------------------------------------------------------

    def _step2_entities(
        self,
        context: str,
        decomposition: Dict[str, Any],
    ) -> List[EntitySpec]:
        """
        Ask the LLM to design all business entities with fields and relationships.

        Returns a list of EntitySpec instances.
        """
        system_prompt = (
            "You are a senior database architect who has designed schemas for applications handling "
            "millions of users. Design a complete, normalised relational data model with proper indexes, "
            "constraints, and audit fields. Think about query patterns, not just data storage. "
            "Typical production apps have 5-10 entities. Return only valid JSON."
        )

        features_hint = ""
        raw_core_features = decomposition.get("core_features", [])
        if raw_core_features:
            # Guard against non-string items in the list (defensive coercion)
            str_features = [str(f) for f in raw_core_features if f][:8]
            if str_features:
                features_hint = "Core features to support: " + ", ".join(str_features)

        prompt = f"""{context}
{features_hint}

Design ALL database entities for this application.

Return a JSON object with this structure:
{{
  "entities": [
    {{
      "name": "EntityName",
      "description": "What this entity represents.",
      "soft_delete": true,
      "timestamps": true,
      "fields": [
        {{
          "name": "field_name",
          "type": "string | integer | decimal | boolean | timestamp | date | text | uuid | object | array",
          "required": true,
          "description": "What this field stores.",
          "validation_rules": ["max_length:255", "unique:true"]
        }}
      ],
      "relationships": [
        {{
          "entity": "OtherEntityName",
          "type": "many-to-one | one-to-many | one-to-one | many-to-many",
          "description": "How these entities relate.",
          "foreign_key": "other_entity_id"
        }}
      ],
      "indexes": ["field_name", "composite:field1,field2"]
    }}
  ]
}}

Rules:
1. Do NOT include id, created_at, updated_at — these are added automatically.
2. Do NOT include the password field in User — handled by auth.
3. Always include a User entity if the app has accounts.
4. Use snake_case for field names.
5. Aim for 4–8 entities covering the core domain.
6. Define relationships bidirectionally (e.g. User has many Posts, Post belongs to User).
7. Be comprehensive — include all fields that the described features would need.
8. Include a status/state field where entities go through a lifecycle (e.g., draft → published → archived).
9. Add audit fields: created_by, updated_by for entities modified by users.
10. Consider adding a Settings or Configuration entity for app-wide settings."""

        response = self._client.complete(
            prompt,
            system_prompt=system_prompt,
            max_tokens=4096,
            temperature=0.3,
            json_mode=True,
        )
        data = safe_parse_json(response.content, step_name="step2_entities")
        if data is None:
            logger.warning("Step 2: could not parse JSON, returning empty entities list")
            return []

        raw_entities = data if isinstance(data, list) else data.get("entities", [])
        entities: List[EntitySpec] = []
        for raw in raw_entities:
            if not isinstance(raw, dict):
                continue
            try:
                # Parse fields
                fields = [
                    FieldSpec(
                        name=f.get("name", "field"),
                        type=f.get("type", "string"),
                        required=f.get("required", True),
                        description=f.get("description", ""),
                        default=f.get("default"),
                        validation_rules=f.get("validation_rules", []),
                    )
                    for f in raw.get("fields", [])
                    if isinstance(f, dict) and f.get("name")
                ]
                # Parse relationships
                relationships = [
                    RelationshipSpec(
                        entity=r.get("entity", ""),
                        type=r.get("type", "many-to-one"),
                        description=r.get("description", ""),
                        foreign_key=r.get("foreign_key"),
                        through_table=r.get("through_table"),
                    )
                    for r in raw.get("relationships", [])
                    if isinstance(r, dict) and r.get("entity")
                ]
                entity = EntitySpec(
                    name=raw.get("name", "Entity"),
                    plural=raw.get("plural", ""),
                    description=raw.get("description", ""),
                    fields=fields,
                    relationships=relationships,
                    soft_delete=raw.get("soft_delete", True),
                    timestamps=raw.get("timestamps", True),
                    indexes=raw.get("indexes", []),
                )
                entities.append(entity)
                logger.debug(
                    f"  Entity '{entity.name}': {len(fields)} fields, "
                    f"{len(relationships)} relationships"
                )
            except Exception as exc:
                logger.warning(f"Step 2: skipping malformed entity {raw.get('name', '?')}: {exc}")

        return entities

    # -------------------------------------------------------------------------
    # Private: Step 3 — API routes
    # -------------------------------------------------------------------------

    def _step3_routes(
        self,
        context: str,
        entities: List[EntitySpec],
        decomposition: Dict[str, Any],
    ) -> List[RouteSpec]:
        """
        Ask the LLM to design RESTful API routes with business logic.

        Returns a list of RouteSpec instances.
        """
        system_prompt = (
            "You are a senior API architect who has built APIs serving millions of requests. "
            "Design a complete, production-quality REST API with proper pagination, filtering, "
            "error handling, and rate limiting considerations. Include both standard CRUD and "
            "domain-specific business operations. Return only valid JSON."
        )

        entity_names = [e.name for e in entities]
        entity_block = (
            f"Entities in the data model: {', '.join(entity_names)}"
            if entity_names
            else ""
        )

        prompt = f"""{context}
{entity_block}

Design all API endpoints for this application.

Return a JSON object with this structure:
{{
  "routes": [
    {{
      "path": "/api/v1/resource",
      "method": "GET | POST | PUT | PATCH | DELETE",
      "summary": "Short description",
      "description": "Detailed description of what this endpoint does.",
      "tags": ["resource-name"],
      "auth_required": true,
      "business_logic": "Step-by-step description of the logic: validate input, check permissions, perform operation, return response.",
      "request_schema": {{
        "fields": {{"field_name": "type description"}},
        "example": {{"field_name": "value"}}
      }},
      "response_schema": {{
        "fields": {{"field_name": "type description"}},
        "example": {{"field_name": "value"}}
      }},
      "status_codes": {{"200": "Success", "400": "Validation error", "401": "Unauthorized"}}
    }}
  ]
}}

Requirements:
1. Always include auth routes: POST /api/v1/auth/register, POST /api/v1/auth/login, POST /api/v1/auth/logout, POST /api/v1/auth/refresh.
2. Always include GET /api/v1/health.
3. For each main entity, include standard CRUD: list (GET), create (POST), retrieve (GET by id), update (PUT/PATCH by id), delete (DELETE by id).
4. Add any business-specific routes the features demand (e.g., /checkout, /publish, /approve).
5. Use RESTful naming conventions with plural nouns.
6. Include pagination query params for list endpoints (page, per_page, sort, filter).
7. Be concise in business_logic — aim for 2–4 sentences.
8. Include rate_limit hint for sensitive endpoints (e.g., auth: "10/min", general: "100/min").
9. For list endpoints, include filter_by and sort_by options in the response.
10. Add a /api/v1/stats or /api/v1/dashboard endpoint that returns aggregate counts/metrics."""

        response = self._client.complete(
            prompt,
            system_prompt=system_prompt,
            max_tokens=4096,
            temperature=0.3,
            json_mode=True,
        )
        data = safe_parse_json(response.content, step_name="step3_routes")
        if data is None:
            logger.warning("Step 3: could not parse JSON, returning empty routes list")
            return []

        raw_routes = data if isinstance(data, list) else data.get("routes", [])
        routes: List[RouteSpec] = []
        for raw in raw_routes:
            if not isinstance(raw, dict):
                continue
            try:
                req = raw.get("request_schema")
                req_schema = (
                    SchemaSpec(
                        fields=req.get("fields", {}),
                        example=req.get("example"),
                    )
                    if isinstance(req, dict)
                    else None
                )
                res = raw.get("response_schema")
                res_schema = (
                    SchemaSpec(
                        fields=res.get("fields", {}),
                        example=res.get("example"),
                    )
                    if isinstance(res, dict)
                    else None
                )
                route = RouteSpec(
                    path=raw.get("path", "/api/v1/unknown"),
                    method=raw.get("method", "GET"),
                    summary=raw.get("summary", ""),
                    description=raw.get("description", ""),
                    tags=raw.get("tags", []),
                    auth_required=raw.get("auth_required", True),
                    request_schema=req_schema,
                    response_schema=res_schema,
                    business_logic=raw.get("business_logic", ""),
                    status_codes=raw.get("status_codes", {}),
                )
                routes.append(route)
            except Exception as exc:
                logger.warning(f"Step 3: skipping malformed route {raw.get('path', '?')}: {exc}")

        return routes

    # -------------------------------------------------------------------------
    # Private: Step 4 — Frontend pages
    # -------------------------------------------------------------------------

    def _step4_pages(
        self,
        context: str,
        entities: List[EntitySpec],
        decomposition: Dict[str, Any],
    ) -> List[PageSpec]:
        """
        Ask the LLM to plan frontend pages and their components.

        Returns a list of PageSpec instances.
        """
        system_prompt = (
            "You are a senior frontend architect and UX designer at a top-tier design agency. "
            "Plan a polished, production-ready page structure with thoughtful component hierarchy, "
            "responsive design considerations, and smooth user journeys. Think about what would "
            "impress investors in a demo. Return only valid JSON."
        )

        entity_names = [e.name for e in entities]
        entity_block = (
            f"Data entities: {', '.join(entity_names)}"
            if entity_names
            else ""
        )
        roles_block = ""
        raw_user_roles = decomposition.get("user_roles", [])
        if raw_user_roles:
            str_roles = [str(r) for r in raw_user_roles if r]
            if str_roles:
                roles_block = "User roles: " + ", ".join(str_roles)

        prompt = f"""{context}
{entity_block}
{roles_block}

Plan all frontend pages for this Next.js application.

Return a JSON object with this structure:
{{
  "pages": [
    {{
      "route": "/dashboard",
      "title": "Dashboard",
      "description": "What the user sees and does on this page.",
      "layout_type": "dashboard | auth | landing | full-width | split | default",
      "auth_required": true,
      "related_entities": ["Entity1", "Entity2"],
      "components": [
        {{
          "name": "ComponentName",
          "type": "table | form | chart | card | modal | hero | navbar | sidebar | stats | list | map | upload | calendar | other",
          "description": "What this component does.",
          "data_source": "entity_name or api_endpoint"
        }}
      ]
    }}
  ]
}}

Requirements:
1. Always include: / (landing or login redirect), /login, /register, /dashboard.
2. Include list and detail/edit pages for each main entity.
3. Include settings and profile pages.
4. For each page with a form, add a form component.
5. For entity list pages, add a table or card-list component plus any relevant charts/stats.
6. Use kebab-case routes.
7. Aim for 8–15 pages covering the full user journey.
8. Include a /analytics or /insights page with charts (even if simple) showing key metrics.
9. Every page should specify at least 2-3 components for a rich, complete experience.
10. Add an /onboarding or /getting-started page for new users."""

        response = self._client.complete(
            prompt,
            system_prompt=system_prompt,
            max_tokens=4096,
            temperature=0.4,
            json_mode=True,
        )
        data = safe_parse_json(response.content, step_name="step4_pages")
        if data is None:
            logger.warning("Step 4: could not parse JSON, returning empty pages list")
            return []

        raw_pages = data if isinstance(data, list) else data.get("pages", [])
        pages: List[PageSpec] = []
        for raw in raw_pages:
            if not isinstance(raw, dict):
                continue
            try:
                components = [
                    ComponentSpec(
                        name=c.get("name", "Component"),
                        type=c.get("type", "generic"),
                        description=c.get("description", ""),
                        data_source=c.get("data_source"),
                    )
                    for c in raw.get("components", [])
                    if isinstance(c, dict)
                ]
                page = PageSpec(
                    route=raw.get("route", "/"),
                    title=raw.get("title", "Page"),
                    description=raw.get("description", ""),
                    layout_type=raw.get("layout_type", "default"),
                    auth_required=raw.get("auth_required", True),
                    components=components,
                    related_entities=raw.get("related_entities", []),
                )
                pages.append(page)
            except Exception as exc:
                logger.warning(f"Step 4: skipping malformed page {raw.get('route', '?')}: {exc}")

        return pages

    # -------------------------------------------------------------------------
    # Private: Step 5 — Cross-cutting concerns
    # -------------------------------------------------------------------------

    def _step5_cross_cutting(
        self,
        context: str,
        entities: List[EntitySpec],
        decomposition: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ask the LLM to define roles, integrations, business rules, and tech stack.

        Returns a dict with keys: roles, integrations, business_rules, tech_stack.
        """
        system_prompt = (
            "You are a senior solutions architect and security specialist. "
            "Define the permission model, required integrations, non-functional rules, "
            "and recommended tech stack for the described application. "
            "Return only valid JSON."
        )

        hints = decomposition.get("tech_stack_hints", {})
        hint_block = (
            "Technical hints from analysis:\n"
            + json.dumps(hints, indent=2)
            if hints
            else ""
        )

        entity_names = [e.name for e in entities]
        entity_block = (
            f"Entities: {', '.join(entity_names)}"
            if entity_names
            else ""
        )

        prompt = f"""{context}
{entity_block}
{hint_block}

Define the cross-cutting concerns for this application.

Return a JSON object with this structure:
{{
  "roles": [
    {{
      "name": "admin",
      "description": "What this role can do.",
      "is_default": false,
      "inherits_from": null,
      "permissions": [
        "users:read", "users:write", "users:delete",
        "resource:read", "resource:write", "resource:delete"
      ]
    }}
  ],
  "integrations": [
    {{
      "name": "Stripe",
      "purpose": "Payment processing and subscription management.",
      "category": "payment | email | storage | auth | analytics | communication | ai | other",
      "required": true,
      "env_vars": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"]
    }}
  ],
  "business_rules": [
    "Users must verify their email before accessing paid features.",
    "Free tier is limited to N resources; paid tier is unlimited."
  ],
  "tech_stack": {{
    "backend_framework": "FastAPI",
    "backend_language": "Python 3.11+",
    "frontend_framework": "Next.js 14",
    "frontend_language": "TypeScript",
    "styling": "Tailwind CSS",
    "database": "PostgreSQL",
    "cache": "Redis",
    "task_queue": "Celery + Redis | null",
    "search_engine": "Elasticsearch | null",
    "object_storage": "AWS S3 | null",
    "containerization": "Docker",
    "ci_cd": "GitHub Actions",
    "hosting": "AWS | Vercel + Render",
    "orm": "SQLAlchemy",
    "auth_method": "JWT + refresh tokens",
    "api_style": "REST",
    "testing": "pytest + Jest"
  }},
  "tech_stack_recommendation": [
    "Python 3.12",
    "FastAPI 0.109",
    "SQLAlchemy 2.0",
    "Pydantic 2.6",
    "PostgreSQL 16",
    "Redis 7.2",
    "React 18.2",
    "Next.js 14.1",
    "TypeScript 5.3",
    "Tailwind CSS 3.4",
    "Alembic 1.13",
    "pytest 8.0",
    "Docker 25"
  ],
  "project_structure": "project-root/\n├── backend/\n│   ├── app/\n│   │   ├── api/\n│   │   │   └── endpoints/\n│   │   ├── core/\n│   │   ├── crud/\n│   │   ├── db/\n│   │   ├── models/\n│   │   ├── schemas/\n│   │   └── main.py\n│   └── requirements.txt\n├── frontend/\n│   ├── src/\n│   │   ├── app/\n│   │   ├── components/\n│   │   ├── lib/\n│   │   └── types/\n│   └── package.json\n└── docker-compose.yml"
}}

Permission format: "resource:action" where action is read/write/delete/admin.
Only include integrations the app genuinely needs based on its features.
Tech stack should be idiomatic for a modern SaaS — prefer the defaults unless the app has special needs.
For tech_stack_recommendation: list specific pinned versions for all major dependencies.
For project_structure: provide a realistic directory tree using ASCII art characters."""

        response = self._client.complete(
            prompt,
            system_prompt=system_prompt,
            max_tokens=3000,
            temperature=0.3,
            json_mode=True,
        )
        data = safe_parse_json(response.content, step_name="step5_cross_cutting")
        if data is None:
            logger.warning("Step 5: could not parse JSON, returning empty cross-cutting dict")
            return {}
        return data

    # -------------------------------------------------------------------------
    # Private: Assembly
    # -------------------------------------------------------------------------

    def _assemble_spec(
        self,
        *,
        idea_name: str,
        idea_description: str,
        decomposition: Dict[str, Any],
        entities: List[EntitySpec],
        routes: List[RouteSpec],
        pages: List[PageSpec],
        cross_cutting: Dict[str, Any],
        features: List[str],
        steps_completed: List[str],
    ) -> SystemSpec:
        """
        Combine outputs from all LLM steps into a single SystemSpec.

        Falls back to a minimal spec if the inputs are empty.
        """
        # ---- Roles ----
        roles: List[RoleSpec] = []
        for raw in cross_cutting.get("roles", []):
            if not isinstance(raw, dict):
                continue
            try:
                roles.append(
                    RoleSpec(
                        name=raw.get("name", "user"),
                        description=raw.get("description", ""),
                        permissions=raw.get("permissions", []),
                        is_default=raw.get("is_default", False),
                        inherits_from=raw.get("inherits_from"),
                    )
                )
            except Exception as exc:
                logger.warning(f"Assembly: skipping malformed role: {exc}")

        # ---- Integrations ----
        integrations: List[IntegrationSpec] = []
        for raw in cross_cutting.get("integrations", []):
            if not isinstance(raw, dict):
                continue
            try:
                integrations.append(
                    IntegrationSpec(
                        name=raw.get("name", "unknown"),
                        purpose=raw.get("purpose", ""),
                        category=raw.get("category", "other"),
                        required=raw.get("required", False),
                        env_vars=raw.get("env_vars", []),
                    )
                )
            except Exception as exc:
                logger.warning(f"Assembly: skipping malformed integration: {exc}")

        # ---- Business rules ----
        business_rules: List[str] = cross_cutting.get(
            "business_rules",
            decomposition.get("business_rules", []),
        )
        if not isinstance(business_rules, list):
            business_rules = []
        # Deduplicate while preserving order
        seen: set = set()
        deduped_rules: List[str] = []
        for rule in business_rules:
            if isinstance(rule, str) and rule not in seen:
                seen.add(rule)
                deduped_rules.append(rule)

        # ---- Tech stack ----
        raw_ts = cross_cutting.get("tech_stack", {})
        if isinstance(raw_ts, dict) and raw_ts:
            try:
                tech_stack = TechStackSpec(**raw_ts)
            except Exception as exc:
                logger.warning(f"Assembly: invalid tech_stack response ({exc}), using default")
                tech_stack = TechStackSpec()
        else:
            tech_stack = TechStackSpec()

        # ---- Description (prefer LLM summary, fall back to raw input) ----
        description = decomposition.get("summary") or idea_description

        # ---- Guard: fall back to minimal spec if steps produced too little ----
        if not entities and not routes and not pages:
            logger.warning(
                "All LLM steps produced empty results — returning fallback spec"
            )
            return self._fallback_spec(idea_name, idea_description, features)

        # Validate that the architect produced a usable spec.
        # If entities have no fields, the code generator will produce empty models.
        usable_entities = [e for e in entities if e.fields]
        if not usable_entities:
            logger.warning(
                "Architect produced %d entities but none have fields — using fallback",
                len(entities),
            )
            return self._fallback_spec(idea_name, idea_description, features)

        # Ensure User entity exists (needed by auth system)
        entity_names = {e.name.lower() for e in entities}
        if "user" not in entity_names:
            logger.info("Architect did not produce a User entity — adding a default one")
            entities.insert(0, EntitySpec(
                name="User",
                description="Application user account.",
                fields=[
                    FieldSpec(name="email", type="string", required=True, description="Unique email address", validation_rules=["unique:true", "format:email"]),
                    FieldSpec(name="full_name", type="string", required=True, description="Display name"),
                    FieldSpec(name="role", type="string", required=True, description="User role", default="member"),
                    FieldSpec(name="is_active", type="boolean", required=True, description="Whether the account is active", default="true"),
                ],
                relationships=[],
                soft_delete=True,
                timestamps=True,
            ))

        # ---- Sprint 6: tech_stack_recommendation ----
        raw_tsr = cross_cutting.get("tech_stack_recommendation", [])
        tech_stack_recommendation: List[str] = [
            str(item) for item in raw_tsr if item
        ] if isinstance(raw_tsr, list) else []

        # ---- Sprint 6: project_structure ----
        project_structure: Optional[str] = cross_cutting.get("project_structure")
        if project_structure and not isinstance(project_structure, str):
            project_structure = None

        # ---- Sprint 6: api_design (derived from routes) ----
        api_design: List[Dict[str, str]] = [
            {
                "method": r.method,
                "path": r.path,
                "description": r.description or r.summary,
            }
            for r in routes
        ]

        return SystemSpec(
            app_name=idea_name,
            description=description,
            entities=entities,
            api_routes=routes,
            pages=pages,
            roles=roles,
            integrations=integrations,
            business_rules=deduped_rules,
            tech_stack=tech_stack,
            features=features if isinstance(features, list) else [],
            tech_stack_recommendation=tech_stack_recommendation,
            project_structure=project_structure,
            api_design=api_design,
            llm_steps_completed=steps_completed,
        )

    # -------------------------------------------------------------------------
    # Private: Fallback
    # -------------------------------------------------------------------------

    def _fallback_spec(
        self,
        idea_name: str,
        idea_description: str,
        features: Optional[List[str]] = None,
    ) -> SystemSpec:
        """
        Return a reasonable minimal SystemSpec when all LLM calls fail.

        This ensures the downstream code generation pipeline always has
        *something* valid to work with, even under complete LLM failure.
        """
        logger.info(f"Generating fallback SystemSpec for '{idea_name}'")
        features = features or []

        # Infer simple feature flags from description text
        desc_lower = idea_description.lower()
        needs_payments = any(
            kw in desc_lower for kw in ("payment", "subscription", "billing", "stripe", "checkout")
        )
        needs_email = any(
            kw in desc_lower for kw in ("email", "notify", "newsletter", "invite", "sendgrid")
        )
        needs_storage = any(
            kw in desc_lower for kw in ("upload", "file", "image", "attachment", "s3", "storage")
        )
        needs_ai = any(kw in desc_lower for kw in ("ai", "llm", "gpt", "openai", "intelligence"))

        # ---- Entities ----
        user_entity = EntitySpec(
            name="User",
            description="Application user account.",
            fields=[
                FieldSpec(name="email", type="string", required=True, description="Unique email address", validation_rules=["unique:true", "format:email"]),
                FieldSpec(name="full_name", type="string", required=True, description="Display name"),
                FieldSpec(name="role", type="string", required=True, description="User role (admin, member, etc.)", default="member"),
                FieldSpec(name="is_active", type="boolean", required=True, description="Whether the account is active", default="true"),
                FieldSpec(name="email_verified", type="boolean", required=True, description="Whether the email has been verified", default="false"),
            ],
            relationships=[],
            soft_delete=True,
            timestamps=True,
        )
        item_entity = EntitySpec(
            name="Item",
            description=f"Core business object for {idea_name}.",
            fields=[
                FieldSpec(name="title", type="string", required=True, description="Title or name"),
                FieldSpec(name="description", type="text", required=False, description="Detailed description"),
                FieldSpec(name="status", type="string", required=True, description="Current status", default="draft"),
                FieldSpec(name="is_published", type="boolean", required=True, description="Whether publicly visible", default="false"),
            ],
            relationships=[
                RelationshipSpec(entity="User", type="many-to-one", description="Created by a user", foreign_key="user_id"),
            ],
            soft_delete=True,
            timestamps=True,
        )
        entities = [user_entity, item_entity]

        # ---- Auth routes ----
        auth_routes = [
            RouteSpec(path="/api/v1/auth/register", method="POST", summary="Register new user", auth_required=False, tags=["auth"], business_logic="Validate email uniqueness, hash password, create user, send verification email, return JWT."),
            RouteSpec(path="/api/v1/auth/login", method="POST", summary="Authenticate user", auth_required=False, tags=["auth"], business_logic="Validate credentials, check account active, return JWT access + refresh tokens."),
            RouteSpec(path="/api/v1/auth/logout", method="POST", summary="Revoke session", auth_required=True, tags=["auth"], business_logic="Invalidate refresh token, return 204."),
            RouteSpec(path="/api/v1/auth/refresh", method="POST", summary="Refresh access token", auth_required=False, tags=["auth"], business_logic="Validate refresh token, issue new access token."),
            RouteSpec(path="/api/v1/health", method="GET", summary="Health check", auth_required=False, tags=["system"], business_logic="Return service status, DB ping, cache ping."),
            RouteSpec(path="/api/v1/users/me", method="GET", summary="Get current user profile", auth_required=True, tags=["users"], business_logic="Return authenticated user's profile."),
            RouteSpec(path="/api/v1/users/me", method="PATCH", summary="Update current user profile", auth_required=True, tags=["users"], business_logic="Validate and apply profile updates."),
        ]
        item_routes = [
            RouteSpec(path="/api/v1/items", method="GET", summary="List items", auth_required=True, tags=["items"], business_logic="Return paginated list filtered by current user."),
            RouteSpec(path="/api/v1/items", method="POST", summary="Create item", auth_required=True, tags=["items"], business_logic="Validate input, create item owned by current user."),
            RouteSpec(path="/api/v1/items/{id}", method="GET", summary="Get item", auth_required=True, tags=["items"], business_logic="Fetch item by ID, verify ownership or permission."),
            RouteSpec(path="/api/v1/items/{id}", method="PATCH", summary="Update item", auth_required=True, tags=["items"], business_logic="Validate input, apply updates, verify ownership."),
            RouteSpec(path="/api/v1/items/{id}", method="DELETE", summary="Delete item", auth_required=True, tags=["items"], business_logic="Soft-delete item, verify ownership or admin role."),
        ]
        routes = auth_routes + item_routes

        # ---- Pages ----
        pages = [
            PageSpec(route="/", title="Home", description="Landing page / redirect to dashboard if authenticated.", layout_type="landing", auth_required=False, components=[ComponentSpec(name="HeroSection", type="hero", description="Value proposition and CTA")]),
            PageSpec(route="/login", title="Login", description="Email + password authentication.", layout_type="auth", auth_required=False, components=[ComponentSpec(name="LoginForm", type="form", description="Email and password fields")]),
            PageSpec(route="/register", title="Sign Up", description="New account registration.", layout_type="auth", auth_required=False, components=[ComponentSpec(name="RegisterForm", type="form", description="Registration fields")]),
            PageSpec(route="/dashboard", title="Dashboard", description="Overview stats and recent activity.", layout_type="dashboard", auth_required=True, related_entities=["Item", "User"], components=[ComponentSpec(name="StatsCards", type="stats", description="Key metrics"), ComponentSpec(name="RecentItems", type="list", description="Recent items")]),
            PageSpec(route="/items", title="Items", description="Manage all items.", layout_type="dashboard", auth_required=True, related_entities=["Item"], components=[ComponentSpec(name="ItemsTable", type="table", description="Sortable, filterable table"), ComponentSpec(name="CreateItemButton", type="other", description="Opens create modal")]),
            PageSpec(route="/items/new", title="New Item", description="Create a new item.", layout_type="dashboard", auth_required=True, related_entities=["Item"], components=[ComponentSpec(name="ItemForm", type="form", description="Item creation form")]),
            PageSpec(route="/items/[id]", title="Item Detail", description="View and edit a single item.", layout_type="dashboard", auth_required=True, related_entities=["Item"], components=[ComponentSpec(name="ItemDetail", type="card", description="Item details"), ComponentSpec(name="ItemEditForm", type="form", description="Edit item fields")]),
            PageSpec(route="/settings", title="Settings", description="Account and application settings.", layout_type="dashboard", auth_required=True, components=[ComponentSpec(name="ProfileForm", type="form", description="Update profile"), ComponentSpec(name="PasswordForm", type="form", description="Change password")]),
        ]

        # ---- Roles ----
        roles = [
            RoleSpec(name="admin", description="Full system access.", permissions=["users:read", "users:write", "users:delete", "items:read", "items:write", "items:delete"], is_default=False),
            RoleSpec(name="member", description="Standard user access.", permissions=["items:read", "items:write"], is_default=True),
        ]

        # ---- Integrations ----
        integrations: List[IntegrationSpec] = []
        if needs_payments:
            integrations.append(IntegrationSpec(name="Stripe", purpose="Payment processing and subscription management.", category="payment", required=True, env_vars=["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"]))
        if needs_email:
            integrations.append(IntegrationSpec(name="SendGrid", purpose="Transactional email delivery.", category="email", required=True, env_vars=["SENDGRID_API_KEY", "EMAIL_FROM_ADDRESS"]))
        if needs_storage:
            integrations.append(IntegrationSpec(name="AWS S3", purpose="Object storage for uploaded files.", category="storage", required=True, env_vars=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]))
        if needs_ai:
            integrations.append(IntegrationSpec(name="OpenAI", purpose="AI-powered features.", category="ai", required=True, env_vars=["OPENAI_API_KEY"]))

        # ---- Business rules ----
        business_rules = [
            "Users must verify their email address before accessing protected features.",
            "Soft-deleted records are excluded from all public queries.",
            "API rate limiting applies to all endpoints to prevent abuse.",
            "All mutations are logged for audit trail.",
            "Admin role has unrestricted access; member role is restricted to own resources.",
        ]

        return SystemSpec(
            app_name=idea_name,
            description=idea_description,
            entities=entities,
            api_routes=routes,
            pages=pages,
            roles=roles,
            integrations=integrations,
            business_rules=business_rules,
            tech_stack=TechStackSpec(),
            features=features,
            # Sprint 6: new fields with sensible fallback defaults
            tech_stack_recommendation=[
                "Python 3.12",
                "FastAPI 0.109",
                "SQLAlchemy 2.0",
                "Pydantic 2.6",
                "PostgreSQL 16",
                "Redis 7.2",
                "React 18.2",
                "Next.js 14.1",
                "TypeScript 5.3",
                "Tailwind CSS 3.4",
            ],
            project_structure=(
                "project-root/\n"
                "├── backend/\n"
                "│   ├── app/\n"
                "│   │   ├── api/endpoints/\n"
                "│   │   ├── core/\n"
                "│   │   ├── crud/\n"
                "│   │   ├── db/\n"
                "│   │   ├── models/\n"
                "│   │   ├── schemas/\n"
                "│   │   └── main.py\n"
                "│   └── requirements.txt\n"
                "├── frontend/\n"
                "│   ├── src/\n"
                "│   │   ├── app/\n"
                "│   │   ├── components/\n"
                "│   │   ├── lib/\n"
                "│   │   └── types/\n"
                "│   └── package.json\n"
                "└── docker-compose.yml"
            ),
            api_design=[
                {"method": r.method, "path": r.path, "description": r.description or r.summary}
                for r in routes
            ],
            llm_steps_completed=["fallback"],
        )

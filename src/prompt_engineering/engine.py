"""
Prompt Engineering Engine
Generates comprehensive product development specifications using LLM.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from src.models import StartupIdea, ProductPrompt, IntelligenceData
from src.config import PipelineConfig
from src.llm import get_llm_client
from src.llm.client import BaseLLMClient

logger = logging.getLogger(__name__)


class PromptEngineeringEngine:
    """
    Generates comprehensive product specifications for startup ideas.
    Uses LLM to create detailed technical and business documentation.
    """
    
    def __init__(self, config: PipelineConfig, llm_client: Optional[BaseLLMClient] = None):
        self.config = config
        self.llm_client = llm_client or get_llm_client()
    
    def generate(
        self,
        idea: StartupIdea,
        intelligence: Optional[IntelligenceData] = None
    ) -> ProductPrompt:
        """
        Generate a comprehensive product prompt for the given idea.
        
        Args:
            idea: The startup idea to generate a prompt for
            intelligence: Optional intelligence data for context
            
        Returns:
            ProductPrompt with complete specification
        """
        logger.info(f"Generating product prompt for: {idea.name}")
        
        # Generate each section
        product_summary = self._generate_product_summary(idea)
        feature_requirements = self._generate_feature_requirements(idea)
        system_architecture = self._generate_system_architecture(idea)
        database_schema = self._generate_database_schema(idea)
        api_specification = self._generate_api_specification(idea)
        ui_ux_outline = self._generate_ui_ux_outline(idea)
        monetization = self._generate_monetization(idea)
        deployment = self._generate_deployment(idea)
        
        prompt_content = {
            "product_summary": product_summary,
            "feature_requirements": feature_requirements,
            "system_architecture": system_architecture,
            "database_schema": database_schema,
            "api_specification": api_specification,
            "ui_ux_outline": ui_ux_outline,
            "monetization": monetization,
            "deployment": deployment
        }
        
        # Convert to JSON string as expected by ProductPrompt model
        prompt_content_str = json.dumps(prompt_content, indent=2)
        
        return ProductPrompt(
            idea_id=idea.id,
            idea_name=idea.name,
            prompt_content=prompt_content_str,
            generation_timestamp=datetime.now(),
            version="1.0"
        )
    
    def _generate_product_summary(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate the product summary section."""
        
        system_prompt = """You are a senior product manager creating a product specification document.
Generate a comprehensive product summary in JSON format. Be specific and detailed."""
        
        prompt = f"""Create a detailed product summary for this startup idea:

**Name:** {idea.name}
**One-liner:** {idea.one_liner}
**Problem:** {idea.problem_statement}
**Solution:** {idea.solution_description}
**Target Buyer:** {idea.target_buyer_persona.model_dump() if hasattr(idea.target_buyer_persona, 'model_dump') else idea.target_buyer_persona}
**Value Proposition:** {idea.value_proposition}

Generate a JSON response with this exact structure:
{{
    "product_name": "string",
    "tagline": "string (max 10 words)",
    "problem_statement": {{
        "primary_problem": "string (detailed)",
        "secondary_problems": ["string", "string"],
        "current_solutions": ["string", "string"],
        "solution_gaps": ["string", "string"]
    }},
    "significance": {{
        "financial_impact": "string (quantified)",
        "operational_impact": "string",
        "strategic_impact": "string"
    }},
    "target_buyer": {{
        "primary": {{
            "job_title": "string",
            "department": "string",
            "company_size": "string",
            "industry_verticals": ["string"],
            "budget_range": "string",
            "success_metrics": ["string"]
        }},
        "secondary": [{{
            "job_title": "string",
            "relationship_to_primary": "string"
        }}],
        "anti_personas": ["string (who this is NOT for)"]
    }},
    "unique_value_proposition": "string (2-3 sentences)"
}}

Respond with ONLY valid JSON, no other text."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=2000, json_mode=True)
            return json.loads(response.content)
        except (Exception, json.JSONDecodeError) as e:
            logger.error(f"Error generating product summary: {e}")
            return self._fallback_product_summary(idea)
    
    def _generate_feature_requirements(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate feature requirements section."""
        
        system_prompt = """You are a senior product manager defining feature requirements.
Create detailed, actionable feature specifications in JSON format."""
        
        prompt = f"""Define the feature requirements for this product:

**Product:** {idea.name}
**Problem:** {idea.problem_statement}
**Solution:** {idea.solution_description}
**Target User:** {idea.target_buyer_persona.title if hasattr(idea.target_buyer_persona, 'title') else 'Business User'}

Generate a JSON response with this structure:
{{
    "core_features": [
        {{
            "id": "F-CORE-001",
            "name": "string",
            "description": "string",
            "user_story": "As a [persona], I want to [action] so that [benefit]",
            "acceptance_criteria": ["string", "string", "string"],
            "priority": "P0-Critical",
            "complexity": "Low|Medium|High",
            "dependencies": []
        }}
    ],
    "secondary_features": [
        {{
            "id": "F-SEC-001",
            "name": "string",
            "description": "string",
            "user_story": "string",
            "acceptance_criteria": ["string"],
            "priority": "P1-Important",
            "complexity": "Low|Medium|High"
        }}
    ],
    "ai_modules": [
        {{
            "id": "AI-001",
            "name": "string",
            "automation_type": "Classification|Generation|Extraction|Prediction|Recommendation",
            "description": "string",
            "input": "string",
            "output": "string",
            "model_requirements": "string",
            "fallback_behavior": "string"
        }}
    ]
}}

Include at least:
- 8 core features (P0)
- 6 secondary features (P1)
- 3 AI/automation modules

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=4000, json_mode=True)
            return json.loads(response.content)
        except (Exception, json.JSONDecodeError) as e:
            logger.error(f"Error generating features: {e}")
            return self._fallback_feature_requirements(idea)
    
    def _generate_system_architecture(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate system architecture section."""
        
        system_prompt = """You are a senior software architect designing a SaaS application.
Provide detailed technical architecture in JSON format."""
        
        prompt = f"""Design the system architecture for this SaaS product:

**Product:** {idea.name}
**Solution:** {idea.solution_description}
**Technical Requirements:** {idea.technical_requirements_summary}

Generate a JSON response with this structure:
{{
    "backend": {{
        "runtime": "Python 3.11+",
        "framework": "FastAPI",
        "api_style": "REST",
        "key_libraries": ["string"]
    }},
    "frontend": {{
        "framework": "Next.js 14",
        "language": "TypeScript",
        "styling": "Tailwind CSS",
        "state_management": "Zustand",
        "component_library": "shadcn/ui"
    }},
    "database": {{
        "primary": "PostgreSQL 15",
        "cache": "Redis",
        "search": "PostgreSQL Full-Text (upgrade to Elasticsearch if needed)",
        "file_storage": "S3-compatible"
    }},
    "authentication": {{
        "method": "JWT with refresh tokens",
        "token_storage": "HttpOnly cookies",
        "oauth_providers": ["Google", "GitHub"],
        "mfa_support": "TOTP",
        "session_duration": "15 min access, 7 day refresh"
    }},
    "external_integrations": [
        {{
            "service": "string",
            "purpose": "string",
            "auth_method": "string",
            "rate_limits": "string"
        }}
    ],
    "infrastructure": {{
        "hosting": "AWS (ECS Fargate) or Vercel + Supabase",
        "cdn": "CloudFront",
        "dns": "Route53",
        "ssl": "ACM"
    }},
    "architecture_diagram_description": "string (describe the architecture flow)"
}}

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=2500, json_mode=True)
            return json.loads(response.content)
        except (Exception, json.JSONDecodeError) as e:
            logger.error(f"Error generating architecture: {e}")
            return self._fallback_system_architecture(idea)
    
    def _generate_database_schema(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate database schema section."""
        
        system_prompt = """You are a database architect designing a schema for a SaaS application.
Provide a complete, normalized database schema in JSON format."""
        
        prompt = f"""Design the database schema for this product:

**Product:** {idea.name}
**Problem:** {idea.problem_statement}
**Solution:** {idea.solution_description}
**Target User:** {idea.target_buyer_persona.title if hasattr(idea.target_buyer_persona, 'title') else 'Business User'}

Generate a JSON response with this structure:
{{
    "entities": [
        {{
            "name": "users",
            "description": "string",
            "fields": [
                {{
                    "name": "id",
                    "type": "UUID",
                    "constraints": ["PRIMARY KEY", "DEFAULT uuid_generate_v4()"]
                }},
                {{
                    "name": "email",
                    "type": "VARCHAR(255)",
                    "constraints": ["UNIQUE", "NOT NULL", "INDEX"]
                }}
            ],
            "relationships": [
                {{
                    "type": "has_many",
                    "target": "other_table",
                    "foreign_key": "user_id"
                }}
            ],
            "indexes": ["email", "created_at"]
        }}
    ],
    "enums": [
        {{
            "name": "subscription_status",
            "values": ["active", "cancelled", "past_due", "trialing"]
        }}
    ],
    "erd_description": "string (describe entity relationships)"
}}

Include at least these entities:
- users (authentication)
- organizations (multi-tenancy)
- subscriptions (billing)
- Plus 4-6 domain-specific entities for {idea.name}

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=4000, json_mode=True)
            return json.loads(response.content)
        except (Exception, json.JSONDecodeError) as e:
            logger.error(f"Error generating schema: {e}")
            return self._fallback_database_schema(idea)
    
    def _generate_api_specification(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate API specification section."""
        
        system_prompt = """You are an API architect designing a RESTful API.
Provide a complete API specification in JSON format."""
        
        prompt = f"""Design the API specification for this product:

**Product:** {idea.name}
**Solution:** {idea.solution_description}

Generate a JSON response with this structure:
{{
    "base_url": "/api/v1",
    "authentication": "Bearer token (JWT)",
    "rate_limiting": "1000 requests/hour per user",
    "endpoints": [
        {{
            "path": "/auth/register",
            "method": "POST",
            "description": "Register a new user",
            "request_body": {{
                "email": "string",
                "password": "string",
                "full_name": "string"
            }},
            "response": {{
                "status": 201,
                "body": {{
                    "user": {{}},
                    "access_token": "string"
                }}
            }},
            "errors": [
                {{"status": 400, "message": "Invalid email format"}},
                {{"status": 409, "message": "Email already registered"}}
            ]
        }}
    ],
    "common_headers": {{
        "Authorization": "Bearer <token>",
        "Content-Type": "application/json"
    }},
    "pagination": {{
        "style": "cursor-based",
        "params": ["cursor", "limit"],
        "default_limit": 20,
        "max_limit": 100
    }},
    "error_format": {{
        "error": {{
            "code": "string",
            "message": "string",
            "details": {{}}
        }}
    }}
}}

Include endpoints for:
- Authentication (register, login, logout, refresh, password reset)
- User management (profile, settings)
- Organization management (CRUD, members, invites)
- Core domain operations (at least 10 endpoints specific to {idea.name})
- Billing (subscription status, plans, checkout)

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=5000, json_mode=True)
            return json.loads(response.content)
        except Exception as e:
            logger.error(f"Error generating API spec: {e}")
            return self._fallback_api_specification(idea)
    
    def _generate_ui_ux_outline(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate UI/UX outline section."""
        
        system_prompt = """You are a UX designer creating a product interface specification.
Provide detailed UI/UX specifications in JSON format."""
        
        prompt = f"""Design the UI/UX outline for this product:

**Product:** {idea.name}
**Target User:** {idea.target_buyer_persona.title if hasattr(idea.target_buyer_persona, 'title') else 'Business User'}
**Solution:** {idea.solution_description}

Generate a JSON response with this structure:
{{
    "design_system": {{
        "primary_color": "#hex",
        "secondary_color": "#hex",
        "font_family": "string",
        "border_radius": "string",
        "spacing_unit": "4px"
    }},
    "user_flows": [
        {{
            "id": "UF-001",
            "name": "User Onboarding",
            "actor": "New User",
            "trigger": "Clicks 'Sign Up'",
            "steps": [
                "1. Enter email and password",
                "2. Verify email",
                "3. Complete profile",
                "4. Choose plan",
                "5. See dashboard"
            ],
            "success_criteria": "User reaches dashboard with sample data",
            "error_states": ["Invalid email", "Weak password", "Verification expired"]
        }}
    ],
    "screens": [
        {{
            "id": "SCR-001",
            "name": "Dashboard",
            "path": "/dashboard",
            "purpose": "Main overview of key metrics and actions",
            "access": "Authenticated",
            "components": ["TopNav", "Sidebar", "MetricsGrid", "RecentActivity", "QuickActions"],
            "data_requirements": ["GET /api/v1/dashboard/summary", "GET /api/v1/activities/recent"]
        }}
    ],
    "components": [
        {{
            "id": "CMP-001",
            "name": "MetricsCard",
            "type": "Display",
            "description": "Card showing a single metric with trend",
            "props": ["title: string", "value: number", "change: number", "trend: up|down|neutral"],
            "variants": ["default", "compact", "expanded"]
        }}
    ],
    "responsive_breakpoints": {{
        "mobile": "< 768px",
        "tablet": "768px - 1024px",
        "desktop": "> 1024px"
    }},
    "accessibility": ["WCAG 2.1 AA compliance", "Keyboard navigation", "Screen reader support", "Color contrast ratios"]
}}

Include:
- At least 6 user flows
- At least 15 screens
- At least 20 components

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=5000, json_mode=True)
            return json.loads(response.content)
        except Exception as e:
            logger.error(f"Error generating UI/UX: {e}")
            return self._fallback_ui_ux_outline(idea)
    
    def _generate_monetization(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate monetization section."""
        
        system_prompt = """You are a SaaS pricing strategist designing a monetization model.
Provide a complete pricing and billing specification in JSON format."""
        
        prompt = f"""Design the monetization strategy for this product:

**Product:** {idea.name}
**Revenue Model:** {idea.revenue_model}
**Pricing Hypothesis:** {idea.pricing_hypothesis}
**Target Buyer:** {idea.target_buyer_persona.model_dump() if hasattr(idea.target_buyer_persona, 'model_dump') else idea.target_buyer_persona}

Generate a JSON response with this structure:
{{
    "pricing_model": "subscription",
    "billing_frequency": ["monthly", "annual"],
    "annual_discount": "20%",
    "tiers": [
        {{
            "name": "Free",
            "price_monthly": 0,
            "price_annual": 0,
            "limits": {{
                "users": 1,
                "projects": 3,
                "storage_gb": 1,
                "api_calls_month": 1000
            }},
            "features": ["Core features", "Community support"],
            "target_segment": "Individual users, evaluation"
        }},
        {{
            "name": "Pro",
            "price_monthly": 29,
            "price_annual": 278,
            "limits": {{
                "users": 5,
                "projects": 20,
                "storage_gb": 10,
                "api_calls_month": 50000
            }},
            "features": ["All Free features", "Advanced analytics", "Priority support", "API access"],
            "target_segment": "Small teams"
        }},
        {{
            "name": "Business",
            "price_monthly": 99,
            "price_annual": 950,
            "limits": {{
                "users": 20,
                "projects": "unlimited",
                "storage_gb": 100,
                "api_calls_month": 500000
            }},
            "features": ["All Pro features", "SSO", "Advanced permissions", "Dedicated support"],
            "target_segment": "Growing companies"
        }},
        {{
            "name": "Enterprise",
            "price_monthly": "custom",
            "price_annual": "custom",
            "limits": {{
                "users": "unlimited",
                "projects": "unlimited",
                "storage_gb": "custom",
                "api_calls_month": "unlimited"
            }},
            "features": ["All Business features", "Custom integrations", "SLA", "Dedicated CSM", "On-premise option"],
            "target_segment": "Large organizations"
        }}
    ],
    "feature_gates": [
        {{
            "feature": "SSO",
            "minimum_tier": "Business",
            "enforcement": "hard"
        }}
    ],
    "billing_provider": "Stripe",
    "trial": {{
        "duration_days": 14,
        "tier": "Pro",
        "requires_card": false
    }},
    "upsell_triggers": [
        "Approaching usage limits",
        "Team size growth",
        "Feature attempts on higher tier"
    ]
}}

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=2500, json_mode=True)
            return json.loads(response.content)
        except Exception as e:
            logger.error(f"Error generating monetization: {e}")
            return self._fallback_monetization(idea)
    
    def _generate_deployment(self, idea: StartupIdea) -> Dict[str, Any]:
        """Generate deployment section."""
        
        system_prompt = """You are a DevOps engineer designing deployment infrastructure.
Provide a complete deployment specification in JSON format."""
        
        prompt = f"""Design the deployment infrastructure for this product:

**Product:** {idea.name}

Generate a JSON response with this structure:
{{
    "environments": ["development", "staging", "production"],
    "ci_cd": {{
        "provider": "GitHub Actions",
        "triggers": {{
            "development": "push to develop branch",
            "staging": "push to main branch",
            "production": "manual approval after staging"
        }},
        "pipeline_steps": [
            "Checkout code",
            "Install dependencies",
            "Run linting",
            "Run unit tests",
            "Run integration tests",
            "Build Docker images",
            "Push to registry",
            "Deploy to environment",
            "Run smoke tests",
            "Notify team"
        ]
    }},
    "infrastructure": {{
        "provider": "AWS",
        "iac_tool": "Terraform",
        "resources": [
            {{
                "name": "ECS Cluster",
                "purpose": "Container orchestration",
                "specs": "Fargate, auto-scaling 2-10 tasks"
            }},
            {{
                "name": "RDS PostgreSQL",
                "purpose": "Primary database",
                "specs": "db.t3.medium, Multi-AZ, 100GB"
            }},
            {{
                "name": "ElastiCache Redis",
                "purpose": "Caching and sessions",
                "specs": "cache.t3.micro, 1 node"
            }},
            {{
                "name": "S3",
                "purpose": "File storage",
                "specs": "Standard, versioning enabled"
            }},
            {{
                "name": "CloudFront",
                "purpose": "CDN for frontend",
                "specs": "Global distribution"
            }},
            {{
                "name": "ALB",
                "purpose": "Load balancing",
                "specs": "Application Load Balancer"
            }}
        ]
    }},
    "containerization": {{
        "backend_image": "python:3.11-slim",
        "frontend_image": "node:20-alpine",
        "registry": "ECR"
    }},
    "monitoring": {{
        "logging": "CloudWatch Logs",
        "metrics": "CloudWatch Metrics",
        "apm": "AWS X-Ray",
        "error_tracking": "Sentry",
        "uptime": "AWS Synthetics"
    }},
    "alerting": [
        {{
            "condition": "Error rate > 1%",
            "duration": "5 minutes",
            "severity": "critical",
            "notification": "PagerDuty"
        }},
        {{
            "condition": "P99 latency > 2s",
            "duration": "10 minutes",
            "severity": "warning",
            "notification": "Slack"
        }},
        {{
            "condition": "CPU > 80%",
            "duration": "5 minutes",
            "severity": "warning",
            "notification": "Slack"
        }}
    ],
    "security": {{
        "ssl": "ACM certificates, TLS 1.3",
        "waf": "AWS WAF with OWASP rules",
        "secrets": "AWS Secrets Manager",
        "encryption": "AES-256 at rest, TLS in transit",
        "backup": "Daily RDS snapshots, 30-day retention"
    }},
    "disaster_recovery": {{
        "rpo": "1 hour",
        "rto": "4 hours",
        "strategy": "Multi-AZ with cross-region backup"
    }}
}}

Respond with ONLY valid JSON."""
        
        try:
            response = self.llm_client.complete(prompt, system_prompt, max_tokens=3000, json_mode=True)
            return json.loads(response.content)
        except Exception as e:
            logger.error(f"Error generating deployment: {e}")
            return self._fallback_deployment(idea)
    
    # Fallback methods for when LLM fails
    def _fallback_product_summary(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "product_name": idea.name,
            "tagline": idea.one_liner[:50],
            "problem_statement": {
                "primary_problem": idea.problem_statement,
                "secondary_problems": [],
                "current_solutions": idea.competitive_landscape[:3],
                "solution_gaps": idea.differentiation_factors
            },
            "significance": {
                "financial_impact": f"TAM: {idea.tam_estimate}",
                "operational_impact": "Reduces manual work significantly",
                "strategic_impact": "Competitive advantage through automation"
            },
            "target_buyer": idea.target_buyer_persona,
            "unique_value_proposition": idea.value_proposition
        }
    
    def _fallback_feature_requirements(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "core_features": [
                {"id": "F-CORE-001", "name": "User Authentication", "priority": "P0-Critical"},
                {"id": "F-CORE-002", "name": "Dashboard", "priority": "P0-Critical"},
                {"id": "F-CORE-003", "name": "Core Workflow", "priority": "P0-Critical"}
            ],
            "secondary_features": [
                {"id": "F-SEC-001", "name": "Reporting", "priority": "P1-Important"},
                {"id": "F-SEC-002", "name": "Integrations", "priority": "P1-Important"}
            ],
            "ai_modules": [
                {"id": "AI-001", "name": "Smart Automation", "automation_type": "Recommendation"}
            ]
        }
    
    def _fallback_system_architecture(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "backend": {"framework": "FastAPI", "runtime": "Python 3.11+"},
            "frontend": {"framework": "Next.js 14", "styling": "Tailwind CSS"},
            "database": {"primary": "PostgreSQL", "cache": "Redis"},
            "authentication": {"method": "JWT"},
            "infrastructure": {"hosting": "AWS"}
        }
    
    def _fallback_database_schema(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "entities": [
                {"name": "users", "fields": [{"name": "id", "type": "UUID"}, {"name": "email", "type": "VARCHAR(255)"}]},
                {"name": "organizations", "fields": [{"name": "id", "type": "UUID"}, {"name": "name", "type": "VARCHAR(255)"}]}
            ]
        }
    
    def _fallback_api_specification(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "base_url": "/api/v1",
            "authentication": "Bearer JWT",
            "endpoints": [
                {"path": "/auth/login", "method": "POST"},
                {"path": "/users/me", "method": "GET"}
            ]
        }
    
    def _fallback_ui_ux_outline(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "screens": [
                {"id": "SCR-001", "name": "Login", "path": "/login"},
                {"id": "SCR-002", "name": "Dashboard", "path": "/dashboard"}
            ],
            "user_flows": [
                {"id": "UF-001", "name": "Login Flow"}
            ],
            "components": [
                {"id": "CMP-001", "name": "Button"}
            ]
        }
    
    def _fallback_monetization(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "pricing_model": idea.revenue_model,
            "tiers": getattr(idea.pricing_hypothesis, "tiers", ["Free", "Pro", "Enterprise"]),
            "billing_provider": "Stripe"
        }
    
    def _fallback_deployment(self, idea: StartupIdea) -> Dict[str, Any]:
        return {
            "ci_cd": {"provider": "GitHub Actions"},
            "infrastructure": {"provider": "AWS", "iac_tool": "Terraform"},
            "containerization": {"registry": "ECR"},
            "monitoring": {"logging": "CloudWatch"}
        }

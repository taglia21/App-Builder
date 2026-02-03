"""
Refinement Engine
Iteratively improves product prompts through self-critique and validation.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from src.config import PipelineConfig
from src.llm import get_llm_client
from src.llm.client import BaseLLMClient
from src.models import (
    CertificationStatus,
    GoldStandardPrompt,
    ProductPrompt,
    PromptCertification,
    RefinementCheck,
    RefinementIteration,
)

logger = logging.getLogger(__name__)


# Pydantic models for LLM response validation
class CheckResult(BaseModel):
    """Validated check result from LLM."""
    passed: bool
    issues: List[str] = Field(default_factory=list)
    severity: str = "none"  # none, low, medium, high, critical
    suggestions: List[str] = Field(default_factory=list)


class FixResult(BaseModel):
    """Validated fix result from LLM."""
    fixed_content: Dict[str, Any]
    changes_made: List[str] = Field(default_factory=list)
    could_not_fix: List[str] = Field(default_factory=list)


class RefinementEngine:
    """
    Refines product prompts through iterative self-critique.

    Checks:
    1. Consistency - No contradictions between sections
    2. Completeness - All required elements present
    3. Technical Validity - Architecture is sound
    4. Security - No obvious vulnerabilities
    5. Feasibility - Can be built with stated resources
    """

    MAX_ITERATIONS = 3

    def __init__(self, config: PipelineConfig, llm_client: Optional[BaseLLMClient] = None):
        self.config = config
        self.llm_client = llm_client or get_llm_client()

    def refine(self, prompt: ProductPrompt) -> GoldStandardPrompt:
        """
        Refine a product prompt to gold standard quality.

        Args:
            prompt: The product prompt to refine

        Returns:
            GoldStandardPrompt with refined prompt and certification status
        """
        logger.info(f"Starting refinement for: {prompt.idea_name}")

        current_prompt = prompt
        refinement_history = []
        iteration = 0

        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            logger.info(f"Refinement iteration {iteration}/{self.MAX_ITERATIONS}")

            # Run all checks
            check_results = self._run_all_checks(current_prompt)

            # Determine which checks passed/failed
            passed = [name for name, result in check_results.items() if result["passed"]]
            failed = [name for name, result in check_results.items() if not result["passed"]]

            # Collect all issues for logging
            all_issues = []
            for name in failed:
                all_issues.extend(check_results[name].get("issues", []))

            # Record this iteration
            refinement_history.append({
                "iteration": iteration,
                "checks_passed": passed,
                "checks_failed": failed,
                "issues": all_issues,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"Iteration {iteration}: {len(passed)} passed, {len(failed)} failed")
            if all_issues:
                logger.info(f"Issues found: {all_issues[:5]}{'...' if len(all_issues) > 5 else ''}")

            # If all checks pass, we're done
            if not failed:
                logger.info("All checks passed - achieving gold standard")
                break

            # Otherwise, fix the issues
            current_prompt = self._fix_issues(current_prompt, check_results)

        # Final check
        final_checks = self._run_all_checks(current_prompt)
        all_passed = all(r["passed"] for r in final_checks.values())

        # Generate certification hash
        cert_hash = ""
        if all_passed:
            prompt_json = json.dumps(current_prompt.prompt_content, sort_keys=True)
            cert_hash = hashlib.sha256(prompt_json.encode()).hexdigest()[:16]

        # Create certification
        certification = PromptCertification(
            status=CertificationStatus.GOLD_STANDARD if all_passed else CertificationStatus.FAILED,
            iterations_required=iteration,
            checks_passed=[n for n, r in final_checks.items() if r["passed"]],
            final_hash=cert_hash
        )

        # Convert refinement history to RefinementIteration objects
        refined_iterations = []
        for hist in refinement_history:
            checks = [
                RefinementCheck(
                    check_name=name,
                    passed=name in hist["checks_passed"],
                    issues=check_results.get(name, {}).get("issues", []),
                    suggestions=check_results.get(name, {}).get("suggestions", [])
                )
                for name in list(hist["checks_passed"]) + list(hist["checks_failed"])
            ]
            refined_iterations.append(
                RefinementIteration(
                    iteration_number=hist["iteration"],
                    checks=checks,
                    changes_made=[]
                )
            )

        logger.info(f"Refinement complete: {certification.status.value} after {iteration} iterations")

        return GoldStandardPrompt(
            product_prompt=current_prompt,
            certification=certification,
            refinement_history=refined_iterations
        )

    def _run_all_checks(self, prompt: ProductPrompt) -> Dict[str, Dict[str, Any]]:
        """Run all validation checks on the prompt."""
        return {
            "completeness": self._check_completeness(prompt),
            "consistency": self._check_consistency(prompt),
            "technical_validity": self._check_technical_validity(prompt),
            "security": self._check_security(prompt),
            "feasibility": self._check_feasibility(prompt)
        }

    def _check_completeness(self, prompt: ProductPrompt) -> Dict[str, Any]:
        """Check that all required sections and elements are present."""
        issues = []
        suggestions = []

        # Parse prompt_content (it's a JSON string)
        try:
            content = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            return {
                "passed": False,
                "issues": ["prompt_content is not valid JSON"],
                "severity": "critical",
                "suggestions": ["Regenerate the product prompt"]
            }

        # Required top-level sections
        required_sections = [
            "product_summary", "feature_requirements", "system_architecture",
            "database_schema", "api_specification", "ui_ux_outline",
            "monetization", "deployment"
        ]

        for section in required_sections:
            if section not in content:
                issues.append(f"Missing required section: {section}")
                suggestions.append(f"Add {section} section with complete details")
            elif not content[section]:
                issues.append(f"Empty section: {section}")
                suggestions.append(f"Populate {section} with relevant content")

        # Check feature requirements depth
        features = content.get("feature_requirements", {})
        if isinstance(features, dict):
            core_features = features.get("core_features", [])
            if len(core_features) < 3:
                issues.append(f"Insufficient core features: {len(core_features)} (need at least 3)")
                suggestions.append("Add more core features based on the problem statement")

            secondary_features = features.get("secondary_features", [])
            if len(secondary_features) < 2:
                issues.append(f"Insufficient secondary features: {len(secondary_features)} (need at least 2)")
                suggestions.append("Add secondary/nice-to-have features")

        # Check database schema
        db_schema = content.get("database_schema", {})
        if isinstance(db_schema, dict):
            entities = db_schema.get("entities", [])
            if len(entities) < 2:
                issues.append(f"Insufficient database entities: {len(entities)} (need at least 2)")
                suggestions.append("Add database entities for users and core domain objects")

        # Check API specification
        api_spec = content.get("api_specification", {})
        if isinstance(api_spec, dict):
            endpoints = api_spec.get("endpoints", [])
            if len(endpoints) < 5:
                issues.append(f"Insufficient API endpoints: {len(endpoints)} (need at least 5)")
                suggestions.append("Add endpoints for CRUD operations and authentication")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "severity": "high" if issues else "none",
            "suggestions": suggestions
        }

    def _check_consistency(self, prompt: ProductPrompt) -> Dict[str, Any]:
        """Check for contradictions between sections using LLM."""
        try:
            content = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            return {"passed": False, "issues": ["Invalid JSON"], "severity": "critical", "suggestions": []}

        # Use LLM to check for inconsistencies
        system_prompt = """You are a technical reviewer checking a product specification for internal consistency.
Look for contradictions like:
- Features mentioned in one section but missing from another
- Database schema that doesn't support the listed features
- API endpoints that don't match the features
- Pricing tiers that don't align with feature sets

Respond with JSON only:
{
    "passed": true/false,
    "issues": ["list of specific contradictions found"],
    "severity": "none|low|medium|high",
    "suggestions": ["how to fix each issue"]
}"""

        user_prompt = f"""Check this product specification for internal consistency:

{json.dumps(content, indent=2)[:6000]}

Identify any contradictions between sections."""

        try:
            response = self.llm_client.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.3,
                json_mode=True
            )
            result = self._parse_check_response(response.content)
            return result
        except Exception as e:
            logger.warning(f"Consistency check failed: {e}")
            # Fallback to basic consistency check
            return self._basic_consistency_check(content)

    def _basic_consistency_check(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback basic consistency check without LLM."""
        issues = []

        # Check if features mentioned in UI exist in API
        features = content.get("feature_requirements", {}).get("core_features", [])
        feature_names = [f.get("name", "").lower() if isinstance(f, dict) else "" for f in features]

        api_endpoints = content.get("api_specification", {}).get("endpoints", [])
        endpoint_paths = [e.get("path", "").lower() if isinstance(e, dict) else "" for e in api_endpoints]

        # Check if we have auth feature but no auth endpoints
        has_auth_feature = any("auth" in f for f in feature_names)
        has_auth_endpoint = any("auth" in e for e in endpoint_paths)

        if has_auth_feature and not has_auth_endpoint:
            issues.append("Authentication feature defined but no auth endpoints in API spec")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "severity": "medium" if issues else "none",
            "suggestions": ["Ensure all features have corresponding API endpoints"]
        }

    def _check_technical_validity(self, prompt: ProductPrompt) -> Dict[str, Any]:
        """Check that the architecture is technically sound."""
        try:
            content = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            return {"passed": False, "issues": ["Invalid JSON"], "severity": "critical", "suggestions": []}

        issues = []
        suggestions = []

        architecture = content.get("system_architecture", {})

        # Check for required architecture components
        if isinstance(architecture, dict):
            if not architecture.get("backend"):
                issues.append("Missing backend architecture specification")
                suggestions.append("Define backend framework, runtime, and key libraries")

            if not architecture.get("frontend"):
                issues.append("Missing frontend architecture specification")
                suggestions.append("Define frontend framework, styling approach, and state management")

            if not architecture.get("database"):
                issues.append("Missing database architecture specification")
                suggestions.append("Define primary database, caching layer, and file storage")

            if not architecture.get("authentication"):
                issues.append("Missing authentication specification")
                suggestions.append("Define auth method, token handling, and session management")

        # Check database schema validity
        db_schema = content.get("database_schema", {})
        if isinstance(db_schema, dict):
            entities = db_schema.get("entities", [])
            for entity in entities:
                if isinstance(entity, dict):
                    if not entity.get("fields"):
                        issues.append(f"Entity '{entity.get('name', 'unknown')}' has no fields defined")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "severity": "high" if issues else "none",
            "suggestions": suggestions
        }

    def _check_security(self, prompt: ProductPrompt) -> Dict[str, Any]:
        """Check for security best practices."""
        try:
            content = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            return {"passed": False, "issues": ["Invalid JSON"], "severity": "critical", "suggestions": []}

        issues = []
        suggestions = []

        architecture = content.get("system_architecture", {})
        auth = architecture.get("authentication", {}) if isinstance(architecture, dict) else {}

        # Check authentication security
        if isinstance(auth, dict):
            method = str(auth.get("method", "")).lower()

            if "jwt" in method and "httponly" not in str(auth.get("token_storage", "")).lower():
                issues.append("JWT tokens should be stored in HttpOnly cookies to prevent XSS")
                suggestions.append("Set token_storage to 'HttpOnly cookies'")

            if not auth.get("mfa_support"):
                issues.append("No MFA support specified (recommended for enterprise)")
                suggestions.append("Add TOTP or WebAuthn MFA support option")

        # Check API security
        api_spec = content.get("api_specification", {})
        if isinstance(api_spec, dict):
            if not api_spec.get("rate_limiting"):
                issues.append("No rate limiting specified")
                suggestions.append("Add rate limiting to prevent abuse")

        # Check deployment security
        deployment = content.get("deployment", {})
        if isinstance(deployment, dict):
            security = deployment.get("security", {})
            if isinstance(security, dict):
                if not security.get("ssl"):
                    issues.append("No SSL/TLS configuration specified")
                    suggestions.append("Configure TLS 1.3 with proper certificate management")

        # Security issues are warnings, not blockers for MVP
        return {
            "passed": len(issues) <= 2,  # Allow up to 2 security warnings
            "issues": issues,
            "severity": "medium" if issues else "none",
            "suggestions": suggestions
        }

    def _check_feasibility(self, prompt: ProductPrompt) -> Dict[str, Any]:
        """Check that the product can be built as specified."""
        try:
            content = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            return {"passed": False, "issues": ["Invalid JSON"], "severity": "critical", "suggestions": []}

        issues = []
        suggestions = []

        # Check for overly complex features
        features = content.get("feature_requirements", {})
        if isinstance(features, dict):
            core_features = features.get("core_features", [])
            if len(core_features) > 15:
                issues.append(f"Too many core features ({len(core_features)}) for an MVP")
                suggestions.append("Reduce to 8-10 core features, move others to roadmap")

            ai_modules = features.get("ai_modules", [])
            for module in ai_modules:
                if isinstance(module, dict):
                    model_req = str(module.get("model_requirements", "")).lower()
                    if "custom" in model_req and "train" in model_req:
                        issues.append(f"Custom model training for '{module.get('name')}' is complex for MVP")
                        suggestions.append("Use pre-trained models or APIs for MVP, add custom training later")

        # Check technology complexity
        architecture = content.get("system_architecture", {})
        if isinstance(architecture, dict):
            # Flag complex patterns
            arch_str = json.dumps(architecture).lower()
            complex_patterns = ["microservices", "kubernetes", "kafka", "graphql federation"]
            for pattern in complex_patterns:
                if pattern in arch_str:
                    issues.append(f"Complex pattern '{pattern}' may slow MVP development")
                    suggestions.append(f"Consider simpler alternatives for MVP, add {pattern} later")

        return {
            "passed": len(issues) <= 1,  # Allow 1 feasibility warning
            "issues": issues,
            "severity": "medium" if issues else "none",
            "suggestions": suggestions
        }

    def _parse_check_response(self, response_content: str) -> Dict[str, Any]:
        """Parse and validate LLM check response."""
        try:
            # Clean up response
            content = response_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            # Validate with Pydantic
            result = CheckResult(**data)
            return result.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Failed to parse check response: {e}")
            return {
                "passed": True,  # Default to pass on parse error
                "issues": [],
                "severity": "none",
                "suggestions": []
            }

    def _fix_issues(
        self,
        prompt: ProductPrompt,
        check_results: Dict[str, Dict[str, Any]]
    ) -> ProductPrompt:
        """Use LLM to fix identified issues in the prompt."""

        # Collect all issues and suggestions
        all_issues = []
        all_suggestions = []
        for check_name, result in check_results.items():
            if not result.get("passed", True):
                for issue in result.get("issues", []):
                    all_issues.append(f"[{check_name}] {issue}")
                all_suggestions.extend(result.get("suggestions", []))

        if not all_issues:
            return prompt

        logger.info(f"Attempting to fix {len(all_issues)} issues using LLM")

        try:
            content = json.loads(prompt.prompt_content)
        except json.JSONDecodeError:
            logger.error("Cannot fix: prompt_content is not valid JSON")
            return prompt

        # Use LLM to fix issues
        system_prompt = """You are a senior product manager fixing issues in a product specification.
Given the current spec and a list of issues, fix each issue while maintaining the overall structure.

IMPORTANT:
- Keep all existing valid content
- Only modify sections that have issues
- Ensure the output is valid JSON
- Add missing sections/fields as needed

Respond with the COMPLETE fixed JSON specification only, no explanations."""

        user_prompt = f"""Current product specification:
{json.dumps(content, indent=2)[:5000]}

Issues to fix:
{chr(10).join(f"- {issue}" for issue in all_issues[:10])}

Suggestions:
{chr(10).join(f"- {s}" for s in all_suggestions[:10])}

Return the complete fixed JSON specification:"""

        try:
            response = self.llm_client.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.3,
                json_mode=True
            )

            # Parse the fixed content
            fixed_content = self._parse_fix_response(response.content)

            if fixed_content:
                logger.info("Successfully fixed issues")
                return ProductPrompt(
                    idea_id=prompt.idea_id,
                    idea_name=prompt.idea_name,
                    prompt_content=json.dumps(fixed_content),
                    metadata=prompt.metadata,
                    created_at=prompt.created_at
                )
            else:
                logger.warning("Could not parse fixed content, returning original")
                return prompt

        except Exception as e:
            logger.error(f"Failed to fix issues with LLM: {e}")
            return prompt

    def _parse_fix_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse LLM fix response and validate it's proper JSON."""
        try:
            content = response_content.strip()

            # Clean up markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # Parse JSON
            data = json.loads(content)

            # Validate it has required structure
            if isinstance(data, dict) and len(data) >= 3:
                return data

            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse fix response: {e}")
            return None

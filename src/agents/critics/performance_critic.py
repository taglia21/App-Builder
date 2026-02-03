"""
Performance Critic Agent - Rival perspective focused on efficiency and optimization.

Part of the Organizational Intelligence framework implementing checks and balances
through specialized rival agents that compete to identify different types of issues.
"""

import json
import logging
import re
from typing import Any, Dict, List

from ..base import LLMProvider
from ..messages import AgentRole, CriticDecision, CriticReview, GeneratedCode

logger = logging.getLogger(__name__)


class PerformanceCritic:
    """
    Performance-focused critic agent that reviews code for efficiency issues.

    This critic represents the "performance engineer" perspective in the
    organizational intelligence framework, specifically looking for:
    - Algorithm complexity issues (O(n²) when O(n) is possible)
    - Memory inefficiencies
    - Database query optimization (N+1 queries, missing indexes)
    - Caching opportunities
    - Async/concurrent execution opportunities
    - Resource leaks
    - Unnecessary computations
    """

    role = AgentRole.CRITIC
    specialty = "performance"

    PERFORMANCE_REVIEW_PROMPT = '''You are a Performance Critic Agent - a specialized performance engineer.

Your role is to review generated code EXCLUSIVELY for performance and efficiency issues.
You are part of a rival multi-agent system where different critics focus on different concerns.

FOCUS ONLY ON PERFORMANCE ISSUES:
- Algorithm complexity (Big O analysis)
- Memory usage and potential leaks
- Database query efficiency (N+1 queries, missing indexes, unoptimized queries)
- Caching opportunities
- Async/concurrent execution opportunities
- Unnecessary loops or computations
- Large data structure inefficiencies
- Resource management (file handles, connections)
- Lazy loading opportunities
- Pagination for large datasets

DO NOT comment on:
- Security (another critic handles this)
- UX concerns (another critic handles this)
- Code style (code_critic handles this)

Code to review:
```
{code}
```

Original requirements:
{requirements}

Respond with JSON:
{{
    "decision": "approve" or "reject" or "needs_revision",
    "performance_score": 0-100,
    "issues": [
        {{
            "severity": "critical|high|medium|low",
            "type": "issue type (e.g., N_PLUS_ONE, O_N_SQUARED, MEMORY_LEAK)",
            "description": "detailed description",
            "location": "filename:line or component",
            "current_complexity": "current Big O if applicable",
            "suggested_complexity": "improved Big O if applicable",
            "recommendation": "how to optimize"
        }}
    ],
    "optimization_opportunities": ["list of potential optimizations"],
    "reasoning": "overall performance assessment"
}}

Be thorough but practical. REJECT only for critical performance issues that would cause
production problems. RECOMMEND revision for significant inefficiencies.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self._antipatterns = self._load_performance_antipatterns()

    def _load_performance_antipatterns(self) -> Dict[str, List[re.Pattern]]:
        """Load regex patterns for common performance anti-patterns."""
        return {
            "nested_loops": [
                re.compile(r'for\s+.*:\s*\n\s+for\s+.*:', re.MULTILINE),
            ],
            "n_plus_one": [
                re.compile(r'for\s+.*:\s*\n.*\.query\(', re.MULTILINE),
                re.compile(r'for\s+.*:\s*\n.*await.*find', re.MULTILINE),
            ],
            "string_concat_loop": [
                re.compile(r'for\s+.*:\s*\n.*\+\=\s*["\']', re.MULTILINE),
                re.compile(r'for\s+.*:\s*\n.*\=.*\+\s*["\']', re.MULTILINE),
            ],
            "sync_in_async": [
                re.compile(r'async\s+def.*:\s*\n(?:.*\n)*?.*time\.sleep\(', re.MULTILINE),
                re.compile(r'async\s+def.*:\s*\n(?:.*\n)*?.*requests\.(?:get|post)', re.MULTILINE),
            ],
            "missing_pagination": [
                re.compile(r'\.all\(\)', re.IGNORECASE),
                re.compile(r'SELECT\s+\*\s+FROM(?!.*LIMIT)', re.IGNORECASE),
            ],
            "repeated_computation": [
                re.compile(r'for\s+.*:\s*\n.*len\(\w+\)', re.MULTILINE),
            ]
        }

    def _static_performance_scan(self, code: str) -> List[Dict[str, Any]]:
        """Perform static analysis for known performance anti-patterns."""
        issues = []

        for issue_type, patterns in self._antipatterns.items():
            for pattern in patterns:
                matches = pattern.findall(code)
                if matches:
                    issues.append({
                        "severity": self._get_severity(issue_type),
                        "type": issue_type.upper(),
                        "description": self._get_description(issue_type),
                        "location": "multiple locations" if len(matches) > 1 else "detected",
                        "recommendation": self._get_recommendation(issue_type)
                    })

        return issues

    def _get_severity(self, issue_type: str) -> str:
        """Get severity level for issue type."""
        severity_map = {
            "nested_loops": "medium",
            "n_plus_one": "high",
            "string_concat_loop": "medium",
            "sync_in_async": "high",
            "missing_pagination": "high",
            "repeated_computation": "low"
        }
        return severity_map.get(issue_type, "medium")

    def _get_description(self, issue_type: str) -> str:
        """Get description for issue type."""
        descriptions = {
            "nested_loops": "Nested loops detected - potential O(n²) complexity",
            "n_plus_one": "N+1 query pattern detected - database queries inside loop",
            "string_concat_loop": "String concatenation in loop - use list join instead",
            "sync_in_async": "Synchronous blocking call in async function",
            "missing_pagination": "Query fetches all records without pagination",
            "repeated_computation": "Repeated computation inside loop that could be cached"
        }
        return descriptions.get(issue_type, "Performance issue detected")

    def _get_recommendation(self, issue_type: str) -> str:
        """Get optimization recommendation for issue type."""
        recommendations = {
            "nested_loops": "Consider using dict/set lookups, or restructure with appropriate data structures",
            "n_plus_one": "Use eager loading (joinedload/selectinload) or batch queries",
            "string_concat_loop": "Collect strings in a list and use ''.join() at the end",
            "sync_in_async": "Use async equivalents: asyncio.sleep(), httpx/aiohttp for HTTP",
            "missing_pagination": "Add LIMIT/OFFSET or use cursor-based pagination",
            "repeated_computation": "Cache the result before the loop"
        }
        return recommendations.get(issue_type, "Review and optimize")

    async def review(self, code: GeneratedCode, requirements: str) -> CriticReview:
        """Review generated code for performance issues."""
        logger.info(f"Performance critic reviewing code for: {requirements[:50]}...")

        # Combine all code files for review
        all_code = "\n\n".join([
            f"# File: {f.filename}\n{f.content}"
            for f in code.files
        ])

        # First, run static analysis
        static_issues = self._static_performance_scan(all_code)

        # Then get LLM-based deep analysis
        prompt = self.PERFORMANCE_REVIEW_PROMPT.format(
            code=all_code,
            requirements=requirements
        )

        response = await self.llm.generate(prompt)

        try:
            review_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse performance critic response as JSON")
            review_data = {
                "decision": "needs_revision",
                "performance_score": 50,
                "issues": static_issues,
                "optimization_opportunities": [],
                "reasoning": "Unable to complete full performance analysis"
            }

        # Merge static analysis findings with LLM findings
        all_issues = static_issues + review_data.get("issues", [])

        # Deduplicate issues
        seen = set()
        unique_issues = []
        for issue in all_issues:
            key = (issue.get("type"), issue.get("description", "")[:50])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        # Determine decision based on issue severities
        decision_map = {
            "approve": CriticDecision.APPROVE,
            "reject": CriticDecision.REJECT,
            "needs_revision": CriticDecision.NEEDS_REVISION
        }

        # Override decision if critical issues found
        has_critical = any(i.get("severity") == "critical" for i in unique_issues)
        high_count = sum(1 for i in unique_issues if i.get("severity") == "high")

        if has_critical or high_count >= 3:
            decision = CriticDecision.REJECT
        elif high_count >= 1:
            decision = CriticDecision.NEEDS_REVISION
        else:
            decision = decision_map.get(
                review_data.get("decision", "approve").lower(),
                CriticDecision.APPROVE
            )

        # Compile suggestions from issues and optimization opportunities
        suggestions = [i.get("recommendation", "") for i in unique_issues if i.get("recommendation")]
        suggestions.extend(review_data.get("optimization_opportunities", []))

        return CriticReview(
            critic_role=self.role,
            specialty=self.specialty,
            decision=decision,
            reasoning=review_data.get("reasoning", "Performance review completed"),
            issues=unique_issues,
            suggestions=suggestions,
            score=review_data.get("performance_score", 50),
            veto_reason=review_data.get("reasoning") if decision == CriticDecision.REJECT else None
        )

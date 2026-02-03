"""
Security Critic Agent - Rival perspective focused on security vulnerabilities.

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


class SecurityCritic:
    """
    Security-focused critic agent that reviews code for vulnerabilities.

    This critic represents the "security auditor" perspective in the
    organizational intelligence framework, specifically looking for:
    - SQL injection vulnerabilities
    - XSS vulnerabilities
    - Authentication/authorization issues
    - Sensitive data exposure
    - Insecure dependencies
    - Input validation gaps
    - CSRF vulnerabilities
    """

    role = AgentRole.CRITIC
    specialty = "security"

    SECURITY_REVIEW_PROMPT = '''You are a Security Critic Agent - a specialized security auditor.

Your role is to review generated code EXCLUSIVELY for security vulnerabilities.
You are part of a rival multi-agent system where different critics focus on different concerns.

FOCUS ONLY ON SECURITY ISSUES:
- SQL injection vulnerabilities
- Cross-site scripting (XSS)
- Authentication/authorization flaws
- Sensitive data exposure (API keys, passwords, tokens)
- Input validation and sanitization
- CSRF vulnerabilities
- Insecure direct object references
- Security misconfigurations
- Injection flaws (command, LDAP, etc.)
- Broken access control

DO NOT comment on:
- Code style or formatting
- Performance (another critic handles this)
- UX concerns (another critic handles this)
- General code quality (code_critic handles this)

Code to review:
```
{code}
```

Original requirements:
{requirements}

Respond with JSON:
{{
    "decision": "approve" or "reject" or "needs_revision",
    "security_score": 0-100,
    "vulnerabilities": [
        {{
            "severity": "critical|high|medium|low",
            "type": "vulnerability type (e.g., SQL_INJECTION, XSS)",
            "description": "detailed description",
            "location": "filename:line or component",
            "recommendation": "how to fix"
        }}
    ],
    "reasoning": "overall security assessment"
}}

Be vigilant but fair. REJECT only for critical/high severity vulnerabilities.
RECOMMEND revision for medium severity. APPROVE if only low severity or none found.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self._known_patterns = self._load_security_patterns()

    def _load_security_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load regex patterns for common security vulnerabilities."""
        return {
            "sql_injection": [
                re.compile(r'execute\s*\(\s*["\'].*%s', re.IGNORECASE),
                re.compile(r'f["\'].*SELECT.*\{', re.IGNORECASE),
                re.compile(r'\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)', re.IGNORECASE),
            ],
            "xss": [
                re.compile(r'innerHTML\s*=', re.IGNORECASE),
                re.compile(r'document\.write\s*\(', re.IGNORECASE),
                re.compile(r'\|\s*safe', re.IGNORECASE),  # Jinja2 safe filter misuse
            ],
            "hardcoded_secrets": [
                re.compile(r'(?:password|secret|api_key|token)\s*=\s*["\'][^"\']+'  , re.IGNORECASE),
                re.compile(r'(?:AWS|AZURE|GCP).*(?:KEY|SECRET)\s*=', re.IGNORECASE),
            ],
            "command_injection": [
                re.compile(r'os\.system\s*\(', re.IGNORECASE),
                re.compile(r'subprocess\.(?:call|run|Popen)\s*\(.*shell\s*=\s*True', re.IGNORECASE),
                re.compile(r'eval\s*\(', re.IGNORECASE),
                re.compile(r'exec\s*\(', re.IGNORECASE),
            ],
            "path_traversal": [
                re.compile(r'open\s*\(.*\+', re.IGNORECASE),
                re.compile(r'os\.path\.join\s*\(.*request', re.IGNORECASE),
            ]
        }

    def _static_security_scan(self, code: str) -> List[Dict[str, Any]]:
        """Perform static analysis for known vulnerability patterns."""
        vulnerabilities = []
        lines = code.split('\n')

        for vuln_type, patterns in self._known_patterns.items():
            for pattern in patterns:
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        vulnerabilities.append({
                            "severity": "high" if vuln_type in ["sql_injection", "command_injection"] else "medium",
                            "type": vuln_type.upper(),
                            "description": f"Potential {vuln_type.replace('_', ' ')} detected",
                            "location": f"line:{i}",
                            "recommendation": self._get_recommendation(vuln_type)
                        })

        return vulnerabilities

    def _get_recommendation(self, vuln_type: str) -> str:
        """Get remediation recommendation for vulnerability type."""
        recommendations = {
            "sql_injection": "Use parameterized queries or ORM methods instead of string formatting",
            "xss": "Sanitize user input and use proper output encoding. Avoid innerHTML.",
            "hardcoded_secrets": "Use environment variables or a secrets manager for sensitive data",
            "command_injection": "Avoid shell=True, use subprocess with list arguments, never use eval/exec with user input",
            "path_traversal": "Validate and sanitize file paths, use os.path.basename() or pathlib"
        }
        return recommendations.get(vuln_type, "Review and remediate the security concern")

    async def review(self, code: GeneratedCode, requirements: str) -> CriticReview:
        """Review generated code for security vulnerabilities."""
        logger.info(f"Security critic reviewing code for: {requirements[:50]}...")

        # Combine all code files for review
        all_code = "\n\n".join([
            f"# File: {f.filename}\n{f.content}"
            for f in code.files
        ])

        # First, run static analysis
        static_vulns = self._static_security_scan(all_code)

        # Then get LLM-based deep analysis
        prompt = self.SECURITY_REVIEW_PROMPT.format(
            code=all_code,
            requirements=requirements
        )

        response = await self.llm.generate(prompt)

        try:
            review_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse security critic response as JSON")
            review_data = {
                "decision": "needs_revision",
                "security_score": 50,
                "vulnerabilities": static_vulns,
                "reasoning": "Unable to complete full security analysis"
            }

        # Merge static analysis findings with LLM findings
        all_vulns = static_vulns + review_data.get("vulnerabilities", [])

        # Deduplicate vulnerabilities
        seen = set()
        unique_vulns = []
        for v in all_vulns:
            key = (v.get("type"), v.get("location"))
            if key not in seen:
                seen.add(key)
                unique_vulns.append(v)

        # Determine decision based on vulnerability severities
        decision_map = {
            "approve": CriticDecision.APPROVE,
            "reject": CriticDecision.REJECT,
            "needs_revision": CriticDecision.NEEDS_REVISION
        }

        # Override decision if critical/high vulns found
        has_critical = any(v.get("severity") == "critical" for v in unique_vulns)
        has_high = any(v.get("severity") == "high" for v in unique_vulns)

        if has_critical:
            decision = CriticDecision.REJECT
        elif has_high:
            decision = CriticDecision.NEEDS_REVISION
        else:
            decision = decision_map.get(
                review_data.get("decision", "needs_revision").lower(),
                CriticDecision.NEEDS_REVISION
            )

        return CriticReview(
            critic_role=self.role,
            specialty=self.specialty,
            decision=decision,
            reasoning=review_data.get("reasoning", "Security review completed"),
            issues=unique_vulns,
            suggestions=[v.get("recommendation", "") for v in unique_vulns if v.get("recommendation")],
            score=review_data.get("security_score", 50),
            veto_reason=review_data.get("reasoning") if decision == CriticDecision.REJECT else None
        )

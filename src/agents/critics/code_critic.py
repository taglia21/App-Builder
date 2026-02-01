"""
Code Critic Agent - Validates generated code.

Implements the veto authority for code quality.
Checks syntax, security, best practices.
"""

from typing import Any, Dict, List, Optional
import ast
import re
import logging

from ..base import CriticAgent, LLMProvider
from ..messages import (
    AgentRole, CriticDecision, CriticReview, GeneratedCode
)

logger = logging.getLogger(__name__)


class CodeCritic(CriticAgent):
    """
    Validates code for syntax, security, and best practices.
    
    Has VETO AUTHORITY - can reject code that fails validation.
    """
    
    # Security patterns to check for
    SECURITY_PATTERNS = [
        (r'eval\s*\(', 'eval() is dangerous - potential code injection'),
        (r'exec\s*\(', 'exec() is dangerous - potential code injection'),
        (r'__import__\s*\(', 'Dynamic imports can be dangerous'),
        (r'subprocess\.call.*shell\s*=\s*True', 'shell=True is dangerous'),
        (r'os\.system\s*\(', 'os.system is dangerous - use subprocess'),
        (r'pickle\.loads?\s*\(', 'Pickle is unsafe with untrusted data'),
        (r'yaml\.load\s*\([^,]*\)', 'Use yaml.safe_load instead'),
        (r'SELECT.*\+.*\+', 'Potential SQL injection'),
        (r'f["\'].*\{.*\}.*SELECT', 'Potential SQL injection in f-string'),
    ]
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        veto_threshold: float = 0.6
    ):
        super().__init__(
            role=AgentRole.CODE_CRITIC,
            agent_id=agent_id,
            llm_provider=llm_provider,
            veto_threshold=veto_threshold
        )
    
    def get_system_prompt(self) -> str:
        return """You are a Code Critic Agent with VETO AUTHORITY.

Your role is to review generated code and decide whether to APPROVE or REJECT.

CRITICAL: You have the power to REJECT code that doesn't meet standards.
Use this power responsibly but firmly. Quality is non-negotiable.

Review criteria:
1. SYNTAX: Is the code syntactically correct?
2. COMPLETENESS: Are all necessary imports present?
3. SECURITY: Are there any security vulnerabilities?
4. BEST PRACTICES: Does it follow coding standards?
5. FUNCTIONALITY: Will the code actually work?

Respond in JSON format:
{
    "decision": "approve" | "reject" | "request_changes",
    "score": 0.0-1.0,
    "reasoning": "Your detailed analysis",
    "issues": [
        {"severity": "critical|high|medium|low", "description": "...", "location": "filename:line"}
    ],
    "suggestions": ["Improvement 1", "Improvement 2"]
}

Be thorough but fair. REJECT only for serious issues."""

    async def review(self, artifact: Any, context: Dict[str, Any]) -> CriticReview:
        """Review code and return decision with veto authority."""
        if isinstance(artifact, GeneratedCode):
            files = artifact.files
        elif isinstance(artifact, dict):
            files = artifact.get("files", artifact)
        else:
            files = {"code": str(artifact)}
        
        # Run static analysis first
        static_issues = self._run_static_analysis(files)
        
        # Run security check
        security_issues = self._check_security(files)
        
        # Combine issues for LLM review
        all_issues = static_issues + security_issues
        
        # If critical issues found, reject immediately
        critical_issues = [i for i in all_issues if i.get("severity") == "critical"]
        if critical_issues:
            return CriticReview(
                critic_role=self.role,
                decision=CriticDecision.REJECT,
                reasoning=f"Found {len(critical_issues)} critical issues",
                issues=critical_issues,
                score=0.0,
                veto_reason="Critical security or syntax issues found"
            )
        
        # Get LLM review for comprehensive analysis
        llm_review = await self._get_llm_review(files, all_issues, context)
        
        return llm_review
    
    def _run_static_analysis(self, files: Dict[str, str]) -> List[Dict]:
        """Run static analysis on Python files."""
        issues = []
        
        for filename, content in files.items():
            if filename.endswith('.py'):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    issues.append({
                        "severity": "critical",
                        "description": f"Syntax error: {e.msg}",
                        "location": f"{filename}:{e.lineno}"
                    })
        
        return issues
    
    def _check_security(self, files: Dict[str, str]) -> List[Dict]:
        """Check for security vulnerabilities."""
        issues = []
        
        for filename, content in files.items():
            for pattern, description in self.SECURITY_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        "severity": "high",
                        "description": description,
                        "location": f"{filename}:{line_num}"
                    })
        
        return issues
    
    async def _get_llm_review(self, files: Dict[str, str], known_issues: List[Dict], context: Dict) -> CriticReview:
        """Get comprehensive LLM review."""
        # Build file summary
        files_summary = "\n\n".join(
            f"=== {name} ===\n{content[:2000]}{'...(truncated)' if len(content) > 2000 else ''}"
            for name, content in files.items()
        )
        
        user_message = f"""Review this generated code:

{files_summary}

Known issues found by static analysis:
{known_issues if known_issues else 'None'}

Context:
{context if context else 'None'}

Provide your review decision in JSON format."""
        
        response = await self._call_llm(user_message, temperature=0.3)
        review_data = self._parse_json_response(response)
        
        # Map decision string to enum
        decision_map = {
            "approve": CriticDecision.APPROVE,
            "reject": CriticDecision.REJECT,
            "request_changes": CriticDecision.REQUEST_CHANGES
        }
        
        decision = decision_map.get(
            review_data.get("decision", "reject").lower(),
            CriticDecision.REJECT
        )
        
        # Combine LLM issues with static analysis issues
        all_issues = known_issues + review_data.get("issues", [])
        
        return CriticReview(
            critic_role=self.role,
            decision=decision,
            reasoning=review_data.get("reasoning", "No reasoning provided"),
            issues=all_issues,
            suggestions=review_data.get("suggestions", []),
            score=review_data.get("score", 0.5),
            veto_reason=review_data.get("reasoning") if decision == CriticDecision.REJECT else None
        )

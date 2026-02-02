"""
UX Critic Agent - Rival perspective focused on user experience and usability.

Part of the Organizational Intelligence framework implementing checks and balances
through specialized rival agents that compete to identify different types of issues.
"""

from typing import Any, Dict, List, Optional
import logging
import json
import re

from ..base import LLMProvider
from ..messages import (
    AgentRole, CriticDecision, CriticReview, GeneratedCode
)

logger = logging.getLogger(__name__)


class UXCritic:
    """
    UX-focused critic agent that reviews code for user experience issues.
    
    This critic represents the "UX designer/advocate" perspective in the
    organizational intelligence framework, specifically looking for:
    - Error handling and user-friendly error messages
    - Loading states and feedback
    - Accessibility (a11y) concerns
    - Responsive design patterns
    - Form validation and user guidance
    - Navigation and information architecture
    - Consistency in UI patterns
    """
    
    role = AgentRole.CRITIC
    specialty = "ux"
    
    UX_REVIEW_PROMPT = '''You are a UX Critic Agent - a specialized user experience advocate.

Your role is to review generated code EXCLUSIVELY for user experience and usability issues.
You are part of a rival multi-agent system where different critics focus on different concerns.

FOCUS ONLY ON UX ISSUES:
- Error handling: Are errors user-friendly? Do they guide users to solutions?
- Loading states: Are there proper loading indicators? Skeleton screens?
- Feedback: Does the UI acknowledge user actions? Success/failure states?
- Accessibility (a11y): ARIA labels, keyboard navigation, color contrast, screen reader support
- Form UX: Validation messages, input hints, required field indicators
- Empty states: What happens when there\'s no data?
- Responsive considerations: Mobile-friendly patterns
- Consistency: Similar actions should work similarly
- Error recovery: Can users easily recover from mistakes?
- Progressive disclosure: Is complexity managed appropriately?

DO NOT comment on:
- Security (another critic handles this)
- Performance (another critic handles this)
- Code quality (code_critic handles this)

Code to review:
```
{code}
```

Original requirements:
{requirements}

Respond with JSON:
{{
    "decision": "approve" or "reject" or "needs_revision",
    "ux_score": 0-100,
    "issues": [
        {{
            "severity": "critical|high|medium|low",
            "type": "issue type (e.g., MISSING_LOADING_STATE, POOR_ERROR_MESSAGE, A11Y_VIOLATION)",
            "description": "detailed description from user perspective",
            "location": "filename:line or component",
            "user_impact": "how this affects the user experience",
            "recommendation": "how to improve"
        }}
    ],
    "accessibility_concerns": ["list of a11y issues"],
    "ux_improvements": ["list of suggested UX enhancements"],
    "reasoning": "overall UX assessment"
}}

Think from the USER\'S perspective. REJECT only for critical UX failures that would
make the app unusable. RECOMMEND revision for significant usability issues.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self._ux_patterns = self._load_ux_patterns()
    
    def _load_ux_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load patterns for UX analysis."""
        return {
            "missing_loading": {
                "positive": [re.compile(r'loading|isLoading|spinner|skeleton', re.IGNORECASE)],
                "description": "No loading state indicators found",
                "severity": "medium"
            },
            "missing_error_handling": {
                "negative": [re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}', re.MULTILINE)],
                "description": "Empty catch block - errors silently swallowed",
                "severity": "high"
            },
            "generic_error_messages": {
                "negative": [re.compile(r'["\'](?:error|something went wrong|an error occurred)["\']', re.IGNORECASE)],
                "description": "Generic error message doesn\'t help users understand or fix the problem",
                "severity": "medium"
            },
            "missing_aria": {
                "positive": [re.compile(r'aria-|role=|alt=', re.IGNORECASE)],
                "description": "Limited accessibility attributes found",
                "severity": "medium"
            },
            "missing_form_validation": {
                "positive": [re.compile(r'required|pattern=|minlength|maxlength|validate', re.IGNORECASE)],
                "description": "Form inputs may lack proper validation",
                "severity": "medium"
            },
            "missing_empty_state": {
                "positive": [re.compile(r'empty|no.?data|no.?results|nothing.?(?:here|found)', re.IGNORECASE)],
                "description": "No empty state handling found",
                "severity": "low"
            }
        }
    
    def _static_ux_scan(self, code: str) -> List[Dict[str, Any]]:
        """Perform static analysis for UX patterns."""
        issues = []
        
        for issue_type, config in self._ux_patterns.items():
            # Check for negative patterns (things that shouldn't be there)
            if "negative" in config:
                for pattern in config["negative"]:
                    if pattern.search(code):
                        issues.append({
                            "severity": config["severity"],
                            "type": issue_type.upper(),
                            "description": config["description"],
                            "location": "detected in code",
                            "user_impact": self._get_user_impact(issue_type),
                            "recommendation": self._get_recommendation(issue_type)
                        })
            
            # Check for positive patterns (things that should be there)
            if "positive" in config:
                found = any(pattern.search(code) for pattern in config["positive"])
                if not found and self._should_have_pattern(issue_type, code):
                    issues.append({
                        "severity": config["severity"],
                        "type": issue_type.upper(),
                        "description": config["description"],
                        "location": "not found in code",
                        "user_impact": self._get_user_impact(issue_type),
                        "recommendation": self._get_recommendation(issue_type)
                    })
        
        return issues
    
    def _should_have_pattern(self, issue_type: str, code: str) -> bool:
        """Determine if code should have certain UX patterns."""
        # Check if code has async operations (should have loading states)
        if issue_type == "missing_loading":
            return bool(re.search(r'async|await|fetch|axios|request', code, re.IGNORECASE))
        # Check if code has forms (should have validation)
        if issue_type == "missing_form_validation":
            return bool(re.search(r'<form|<input|FormData|handleSubmit', code, re.IGNORECASE))
        # Check if code has lists/data display (should have empty states)
        if issue_type == "missing_empty_state":
            return bool(re.search(r'\.map\(|forEach|<ul|<table|list', code, re.IGNORECASE))
        # Check if code has interactive elements (should have ARIA)
        if issue_type == "missing_aria":
            return bool(re.search(r'<button|onClick|<a\s|href=', code, re.IGNORECASE))
        return False
    
    def _get_user_impact(self, issue_type: str) -> str:
        """Get user impact description for issue type."""
        impacts = {
            "missing_loading": "Users don\'t know if the app is working, may click multiple times or leave",
            "missing_error_handling": "Users see nothing when errors occur, leaving them confused",
            "generic_error_messages": "Users can\'t understand what went wrong or how to fix it",
            "missing_aria": "Screen reader users and keyboard-only users may not be able to use the app",
            "missing_form_validation": "Users may submit invalid data and not understand why it failed",
            "missing_empty_state": "Users see a blank screen and don\'t know if it\'s loading, broken, or just empty"
        }
        return impacts.get(issue_type, "Negatively affects user experience")
    
    def _get_recommendation(self, issue_type: str) -> str:
        """Get UX recommendation for issue type."""
        recommendations = {
            "missing_loading": "Add loading indicators (spinners, skeletons) for async operations",
            "missing_error_handling": "Catch errors and display user-friendly messages with recovery options",
            "generic_error_messages": "Provide specific, actionable error messages that help users resolve issues",
            "missing_aria": "Add ARIA labels, roles, and ensure keyboard navigation works",
            "missing_form_validation": "Add client-side validation with clear error messages near each field",
            "missing_empty_state": "Design empty states with helpful messages and calls-to-action"
        }
        return recommendations.get(issue_type, "Improve user experience")
    
    async def review(self, code: GeneratedCode, requirements: str) -> CriticReview:
        """Review generated code for UX issues."""
        logger.info(f"UX critic reviewing code for: {requirements[:50]}...")
        
        # Combine all code files for review
        all_code = "\n\n".join([
            f"# File: {f.filename}\n{f.content}" 
            for f in code.files
        ])
        
        # First, run static analysis
        static_issues = self._static_ux_scan(all_code)
        
        # Then get LLM-based deep analysis
        prompt = self.UX_REVIEW_PROMPT.format(
            code=all_code,
            requirements=requirements
        )
        
        response = await self.llm.generate(prompt)
        
        try:
            review_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse UX critic response as JSON")
            review_data = {
                "decision": "needs_revision",
                "ux_score": 50,
                "issues": static_issues,
                "accessibility_concerns": [],
                "ux_improvements": [],
                "reasoning": "Unable to complete full UX analysis"
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
        a11y_issues = len(review_data.get("accessibility_concerns", []))
        
        if has_critical:
            decision = CriticDecision.REJECT
        elif high_count >= 2 or a11y_issues >= 3:
            decision = CriticDecision.NEEDS_REVISION
        else:
            decision = decision_map.get(
                review_data.get("decision", "approve").lower(),
                CriticDecision.APPROVE
            )
        
        # Compile suggestions from issues and improvements
        suggestions = [i.get("recommendation", "") for i in unique_issues if i.get("recommendation")]
        suggestions.extend(review_data.get("ux_improvements", []))
        suggestions.extend([f"A11y: {c}" for c in review_data.get("accessibility_concerns", [])])
        
        return CriticReview(
            critic_role=self.role,
            specialty=self.specialty,
            decision=decision,
            reasoning=review_data.get("reasoning", "UX review completed"),
            issues=unique_issues,
            suggestions=suggestions,
            score=review_data.get("ux_score", 50),
            veto_reason=review_data.get("reasoning") if decision == CriticDecision.REJECT else None
        )

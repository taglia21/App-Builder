"""
Code Writer Agent - Generates application code.

Responsible for producing code artifacts that will be
validated by critic agents before being shown to users.
"""

from typing import Any, Dict, List, Optional
import json
import logging

from ..base import WriterAgent, LLMProvider
from ..messages import (
    AgentRole, ExecutionPlan, CodeGenerationRequest, GeneratedCode
)

logger = logging.getLogger(__name__)


class CodeWriterAgent(WriterAgent):
    """
    Generates application code based on execution plans.
    
    Key principle: Writers produce artifacts for validation,
    not for immediate execution.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        super().__init__(
            role=AgentRole.CODE_WRITER,
            agent_id=agent_id,
            llm_provider=llm_provider
        )
        self.tech_stack_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict]:
        """Load tech stack templates."""
        return {
            "fastapi": {
                "main_file": "main.py",
                "base_imports": [
                    "from fastapi import FastAPI, HTTPException, Depends",
                    "from pydantic import BaseModel",
                    "from typing import List, Optional"
                ],
                "app_init": "app = FastAPI(title='{app_name}')"
            },
            "flask": {
                "main_file": "app.py",
                "base_imports": [
                    "from flask import Flask, jsonify, request"
                ],
                "app_init": "app = Flask(__name__)"
            },
            "django": {
                "main_file": "manage.py",
                "base_imports": [],
                "app_init": ""
            },
            "express": {
                "main_file": "index.js",
                "base_imports": [
                    "const express = require('express');"
                ],
                "app_init": "const app = express();"
            },
            "nextjs": {
                "main_file": "pages/index.tsx",
                "base_imports": [
                    "import type { NextPage } from 'next'"
                ],
                "app_init": ""
            }
        }
    
    def get_system_prompt(self) -> str:
        return """You are a Code Writer Agent for an AI-powered app builder.

Your role is to generate high-quality, production-ready code based on execution plans.

RULES:
1. Generate COMPLETE, WORKING code - no placeholders or TODOs
2. Follow best practices for the specified tech stack
3. Include proper error handling
4. Add helpful comments explaining the code
5. Ensure all imports are included
6. Generate requirements.txt or package.json as needed

If you receive feedback from a critic, incorporate their suggestions.

Respond with JSON containing all generated files:
{
    "files": {
        "filename.py": "file content",
        "another_file.py": "content"
    },
    "dependencies": ["package1", "package2"],
    "execution_instructions": "How to run the app"
}

Generate complete, working code that meets all acceptance criteria."""

    async def write(self, request: Any) -> GeneratedCode:
        """Generate code from a request."""
        if isinstance(request, CodeGenerationRequest):
            return await self._generate_from_request(request)
        elif isinstance(request, dict):
            if "plan" in request:
                return await self._generate_from_request(
                    CodeGenerationRequest(**request)
                )
            # Direct generation from description
            return await self._generate_from_description(request)
        else:
            raise ValueError(f"Unsupported request type: {type(request)}")
    
    async def _generate_from_request(self, request: CodeGenerationRequest) -> GeneratedCode:
        """Generate code from a formal request with plan."""
        plan = request.plan
        
        # Build the user message
        user_message = self._build_generation_prompt(plan, request)
        
        # Get code from LLM
        response = await self._call_llm(user_message, temperature=0.3)
        
        # Parse the response
        code_data = self._parse_json_response(response)
        
        return GeneratedCode(
            files=code_data.get("files", {}),
            tech_stack=plan.tech_stack,
            dependencies=code_data.get("dependencies", []),
            execution_instructions=code_data.get("execution_instructions"),
            metadata={
                "plan_id": plan.plan_id,
                "retry_count": request.retry_count
            }
        )
    
    async def _generate_from_description(self, request: Dict) -> GeneratedCode:
        """Generate code directly from a description (simpler flow)."""
        description = request.get("description", "")
        tech_stack = request.get("tech_stack", "fastapi")
        
        user_message = f"""Generate a complete {tech_stack} application:

Description: {description}

Generate all necessary files with complete, working code.

Respond in JSON format with files, dependencies, and execution_instructions."""
        
        response = await self._call_llm(user_message, temperature=0.3)
        code_data = self._parse_json_response(response)
        
        return GeneratedCode(
            files=code_data.get("files", {}),
            tech_stack=tech_stack,
            dependencies=code_data.get("dependencies", []),
            execution_instructions=code_data.get("execution_instructions")
        )
    
    def _build_generation_prompt(self, plan: ExecutionPlan, request: CodeGenerationRequest) -> str:
        """Build the prompt for code generation."""
        prompt = f"""Generate code for this application:

Description: {plan.app_description}

Tech Stack: {plan.tech_stack}

Acceptance Criteria (YOUR CODE MUST SATISFY ALL OF THESE):
{chr(10).join(f'- {c}' for c in plan.acceptance_criteria)}

Required Files: {', '.join(plan.metadata.get('required_files', []))}
"""
        
        # Add feedback if this is a retry
        if request.previous_feedback:
            prompt += f"""\n\nPREVIOUS ATTEMPT FEEDBACK (FIX THESE ISSUES):
{request.previous_feedback}
"""
        
        prompt += """\n\nGenerate complete, working code in JSON format."""
        
        return prompt

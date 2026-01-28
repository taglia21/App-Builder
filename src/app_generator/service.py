"""App Generator Service - Real LLM integration."""
import os
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
import anthropic
import openai
from .models import (
    GenerationRequest, GeneratedApp, GeneratedFile, GenerationProgress,
    TechStack, Feature
)
from .templates import TemplateManager

logger = logging.getLogger(__name__)


class AppGeneratorService:
    """Service for generating complete applications using LLM."""
    
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.use_anthropic = bool(self.anthropic_key)
        self.template_manager = TemplateManager()
        
        if self.use_anthropic:
            self.client = anthropic.Anthropic(api_key=self.anthropic_key)
        elif self.openai_key:
            openai.api_key = self.openai_key
        else:
            logger.warning("No LLM API keys found - will use template generation only")
    
    async def generate_app(self, request: GenerationRequest) -> AsyncGenerator[GenerationProgress, None]:
        """Generate complete app with real-time progress updates."""
        try:
            # Step 1: Analyze requirements
            yield GenerationProgress(
                step="analyze",
                progress=10,
                message="Analyzing your idea...",
                total_files=10
            )
            
            spec = await self._analyze_requirements(request)
            
            # Step 2: Generate architecture
            yield GenerationProgress(
                step="architecture",
                progress=25,
                message="Designing database schema...",
                total_files=10
            )
            
            architecture = await self._generate_architecture(request, spec)
            
            # Step 3: Generate code files
            yield GenerationProgress(
                step="generation",
                progress=40,
                message="Generating API routes...",
                total_files=10
            )
            
            files = []
            file_generators = [
                self._generate_main_file(request, architecture),
                self._generate_models_file(request, architecture),
                self._generate_routes_file(request, architecture),
                self._generate_database_file(request, architecture),
            ]
            
            if Feature.AUTH in request.features:
                file_generators.append(self._generate_auth_file(request))
            
            if Feature.PAYMENTS in request.features:
                file_generators.append(self._generate_payments_file(request))
            
            for i, gen in enumerate(file_generators):
                file = await gen
                files.append(file)
                yield GenerationProgress(
                    step="generation",
                    progress=40 + int((i + 1) / len(file_generators) * 30),
                    message=f"Generated {file.path}",
                    files_generated=i + 1,
                    total_files=len(file_generators)
                )

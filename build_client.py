#!/usr/bin/env python3
"""Script to complete the LLM client file with Mock and factory functions."""

mock_client_code = '''

class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API calls."""
    
    provider_name = "mock"
    
    def __init__(self):
        logger.info("Initialized Mock LLM client (no API calls)")
    
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        if json_mode:
            content = self._generate_mock_json(prompt)
        else:
            content = f"[MOCK RESPONSE] Processed prompt of {len(prompt)} characters."
        
        return LLMResponse(
            content=content,
            model="mock-model",
            provider=self.provider_name,
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4},
            latency_ms=10
        )
    
    def _generate_mock_json(self, prompt: str) -> str:
        """Generate contextual mock JSON based on prompt content."""
        prompt_lower = prompt.lower()
        
        if "product summary" in prompt_lower:
            return json.dumps({
                "product_name": "Mock Product",
                "tagline": "A mock product for testing",
                "problem_statement": {
                    "primary_problem": "This is a mock problem statement",
                    "secondary_problems": ["Secondary problem 1"],
                    "current_solutions": ["Existing solution 1"],
                    "solution_gaps": ["Gap 1"]
                },
                "significance": {
                    "financial_impact": "$1M potential savings",
                    "operational_impact": "50% time reduction",
                    "strategic_impact": "Competitive advantage"
                },
                "target_buyer": {"title": "Manager", "company_size": "50-500"},
                "unique_value_proposition": "Mock value proposition"
            })
        
        elif "feature" in prompt_lower:
            return json.dumps({
                "core_features": [
                    {"id": "F-CORE-001", "name": "Mock Feature 1", "priority": "P0-Critical", "description": "A mock core feature"}
                ],
                "secondary_features": [
                    {"id": "F-SEC-001", "name": "Mock Secondary Feature", "priority": "P1-Important"}
                ],
                "ai_modules": [
                    {"id": "AI-001", "name": "Mock AI Module", "automation_type": "Generation"}
                ]
            })
        
        elif "architecture" in prompt_lower:
            return json.dumps({
                "backend": {"framework": "FastAPI", "runtime": "Python 3.11+"},
                "frontend": {"framework": "Next.js 14", "styling": "Tailwind CSS"},
                "database": {"primary": "PostgreSQL", "cache": "Redis"},
                "authentication": {"method": "JWT"},
                "infrastructure": {"hosting": "AWS"}
            })
        
        elif "database" in prompt_lower or "schema" in prompt_lower:
            return json.dumps({
                "entities": [
                    {"name": "users", "fields": [{"name": "id", "type": "UUID"}, {"name": "email", "type": "VARCHAR(255)"}]},
                    {"name": "organizations", "fields": [{"name": "id", "type": "UUID"}, {"name": "name", "type": "VARCHAR(255)"}]}
                ]
            })
        
        elif "api" in prompt_lower or "endpoint" in prompt_lower:
            return json.dumps({
                "base_url": "/api/v1",
                "authentication": "Bearer JWT",
                "endpoints": [
                    {"path": "/auth/login", "method": "POST"},
                    {"path": "/auth/register", "method": "POST"},
                    {"path": "/users/me", "method": "GET"}
                ]
            })
        
        elif "ui" in prompt_lower or "ux" in prompt_lower:
            return json.dumps({
                "screens": [
                    {"id": "SCR-001", "name": "Dashboard", "path": "/dashboard"},
                    {"id": "SCR-002", "name": "Login", "path": "/login"}
                ],
                "user_flows": [{"id": "UF-001", "name": "Login Flow"}],
                "components": [{"id": "CMP-001", "name": "Button"}]
            })
        
        elif "monetization" in prompt_lower or "pricing" in prompt_lower:
            return json.dumps({
                "pricing_model": "subscription",
                "tiers": [
                    {"name": "Free", "price_monthly": 0},
                    {"name": "Pro", "price_monthly": 29},
                    {"name": "Enterprise", "price_monthly": "custom"}
                ],
                "billing_provider": "Stripe"
            })
        
        elif "deployment" in prompt_lower:
            return json.dumps({
                "ci_cd": {"provider": "GitHub Actions"},
                "infrastructure": {"provider": "AWS", "iac_tool": "Terraform"},
                "monitoring": {"logging": "CloudWatch"}
            })
        
        elif "consistency" in prompt_lower or "check" in prompt_lower:
            return json.dumps({
                "passed": True,
                "issues": [],
                "severity": "none"
            })
        
        elif "feasibility" in prompt_lower:
            return json.dumps({
                "passed": True,
                "issues": [],
                "severity": "none",
                "estimated_mvp_weeks": 8
            })
        
        else:
            return json.dumps({"mock": True, "message": "Mock response generated"})


class MultiProviderClient(BaseLLMClient):
    """Client that can failover between multiple providers."""
    
    provider_name = "multi"
    
    def __init__(self, providers: List[BaseLLMClient]):
        self.providers = providers
        logger.info(f"Initialized MultiProvider client with {len(providers)} providers")
    
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        last_error = None
        
        for provider in self.providers:
            try:
                logger.info(f"Trying provider: {provider.provider_name}")
                response = provider.complete(prompt, system_prompt, max_tokens, temperature, json_mode)
                logger.info(f"Success with provider: {provider.provider_name}")
                return response
            except Exception as e:
                logger.warning(f"Provider {provider.provider_name} failed: {e}")
                last_error = e
                continue
        
        raise Exception(f"All providers failed. Last error: {last_error}")


def get_llm_client(
    provider: str = "auto",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMClient:
    """Factory function to get an LLM client."""
    
    if provider == "auto":
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "auto")
    
    if provider == "mock":
        return MockLLMClient()
    
    if provider == "gemini":
        return GeminiClient(
            api_key=api_key,
            model=model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        )
    
    if provider == "groq":
        return GroqClient(
            api_key=api_key,
            model=model or os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        )
    
    if provider == "openrouter":
        return OpenRouterClient(
            api_key=api_key,
            model=model or os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        )
    
    if provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            model=model or os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        )
    
    if provider == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        )
    
    if provider == "multi":
        providers = []
        
        if os.getenv("GROQ_API_KEY"):
            try:
                providers.append(GroqClient())
            except:
                pass
        
        if os.getenv("GOOGLE_API_KEY"):
            try:
                providers.append(GeminiClient())
            except:
                pass
        
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                providers.append(OpenRouterClient())
            except:
                pass
        
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                providers.append(AnthropicClient())
            except:
                pass
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                providers.append(OpenAIClient())
            except:
                pass
        
        if not providers:
            logger.warning("No providers available for multi-provider client, using mock")
            return MockLLMClient()
        
        return MultiProviderClient(providers)
    
    if provider == "auto":
        # Try providers in order (free/fast first)
        if os.getenv("GROQ_API_KEY"):
            try:
                return GroqClient()
            except Exception as e:
                logger.warning(f"Could not initialize Groq: {e}")
        
        if os.getenv("GOOGLE_API_KEY"):
            try:
                return GeminiClient()
            except Exception as e:
                logger.warning(f"Could not initialize Gemini: {e}")
        
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                return OpenRouterClient()
            except Exception as e:
                logger.warning(f"Could not initialize OpenRouter: {e}")
        
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                return AnthropicClient()
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic: {e}")
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                return OpenAIClient()
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI: {e}")
        
        logger.warning("No API keys found, using mock client")
        return MockLLMClient()
    
    raise ValueError(f"Unknown provider: {provider}")


def list_available_providers() -> Dict[str, bool]:
    """Check which providers are available based on environment variables."""
    return {
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mock": True
    }
'''

# Append to the file
with open('src/llm/client_new.py', 'a') as f:
    f.write(mock_client_code)

print("✓ Added MockClient, MultiProviderClient, and factory functions")
print(f"✓ Total lines in client_new.py: {sum(1 for _ in open('src/llm/client_new.py'))}")

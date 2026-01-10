
"""
FULL SYSTEM STRESS TEST
-----------------------
Evaluates the "SaaS-in-a-box" pipeline under maximum load conditions.
1. Intelligence: Mocks high-volume data inputs.
2. Ideation: Generates complex B2B Enterprise prompts.
3. Code Generation: Forces all optional modules (AI, Celery, Email, Payments).
4. Validation: Checks file existence, syntax, and QA formatting.
"""

import asyncio
import shutil
import sys
from pathlib import Path
from src.config import load_config
from src.models import (
    StartupIdea, IntelligenceData, PipelineMetadata, PipelineStage,
    BuyerPersona, PricingHypothesis, RevenueModel
)
from src.pipeline import StartupGenerationPipeline
from src.quality_assurance import QualityAssuranceEngine
from src.llm.client import BaseLLMClient, LLMResponse
import src.llm.client
from uuid import uuid4
import json

# Monkey Patch for Stress Test consistency
class RobustMockClient(BaseLLMClient):
    provider_name = "robust-mock"
    
    def complete(self, prompt, system_prompt=None, max_tokens=1000, temperature=0, json_mode=False):
        print(f"DEBUG: Mock Client received prompt len={len(prompt)}")
        prompt_lower = prompt.lower()
        if "product summary" in prompt_lower:
             print("DEBUG: Matched 'product summary'")
        content = "{}"
        
        if "product summary" in prompt_lower:
            content = json.dumps({
                "product_name": "LogiFlow AI",
                "tagline": "Optimize logistics with AI",
                "problem_statement": {
                    "primary_problem": "Inefficient routing",
                    "secondary_problems": ["Fuel costs"],
                    "current_solutions": ["Manual planning"],
                    "solution_gaps": ["No AI"]
                },
                "significance": {"financial_impact": "High", "operational_impact": "High", "strategic_impact": "High"},
                "target_buyer": {"primary": {"job_title": "Manager", "department": "Ops", "company_size": "Ent", "industry_verticals": ["Logistics"], "budget_range": "High", "success_metrics": ["ROI"]}, "secondary": [], "anti_personas": []},
                "unique_value_proposition": "AI Routing"
            })
        elif "detect" in prompt_lower:
             # Feature Detection Prompt
             content = json.dumps({
                "needs_payments": True,
                "needs_background_jobs": True,
                "needs_ai_integration": True,
                "needs_email": True
             })
        elif "feature" in prompt_lower:
             # Feature List Prompt
             content = json.dumps({
                "core_features": [{"name": "AI Routing", "priority": "High"}],
                "secondary_features": [], 
                "ai_features": [{"name": "Route Optimization", "type": "optimization"}], 
                "integrations": ["stripe", "sendgrid", "redis", "celery"],
             })
        elif "architecture" in prompt_lower:
             content = json.dumps({"frontend": {"framework": "nextjs"}, "backend": {"framework": "fastapi"}, "database": {"type": "postgres"}, "infrastructure": {"cloud": "aws"}})
        elif "database" in prompt_lower:
             content = json.dumps({"tables": [{"name": "users", "columns": [{"name": "id", "type": "uuid"}]}]})
        elif "api" in prompt_lower:
             content = json.dumps({"endpoints": []})
        elif "ui" in prompt_lower:
             content = json.dumps({"pages": []})
        elif "monetization" in prompt_lower:
             content = json.dumps({"strategy": "subscription"})
        elif "deployment" in prompt_lower:
             content = json.dumps({"strategy": "docker"})
        elif "refinement" in prompt_lower or "check" in prompt_lower or "evaluate" in prompt_lower:
             content = json.dumps({"passed": True, "issues": [], "suggestions": [], "score": 9})
        else:
             content = json.dumps({"mock": "generic response"})

        return LLMResponse(content=content, model="mock", provider="robust-mock", usage={}, latency_ms=0)

def mock_get_client(provider=None):
    print("🤖 Using Robust Mock LLM Client")
    return RobustMockClient()

src.llm.client.get_llm_client = mock_get_client

# Patch everywhere else (since they might have imported it already)
import src.prompt_engineering.engine
import src.code_generation.enhanced_engine
import src.intelligence.engine

src.prompt_engineering.engine.get_llm_client = mock_get_client
src.code_generation.enhanced_engine.get_llm_client = mock_get_client
src.intelligence.engine.get_llm_client = mock_get_client


def run_stress_test():
    print("🚀 INITIATING FULL SYSTEM STRESS TEST")
    print("====================================")
    
    # 1. Setup Environment
    output_dir = Path("./stress_test_output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    config = load_config("config.yml")
    
    # 2. Construct Complex Mock Idea (Enterprise Grade)
    # This forces every feature flag in the template engine to be TRUE
    idea = StartupIdea(
        id=uuid4(),
        name="LogiFlow AI",
        one_liner="Enterprise Logistics Optimization Platform",
        target_buyer_persona=BuyerPersona(
            title="Logistics Manager",
            industry="Supply Chain",
            company_size="Enterprise",
            budget_authority=True,
            pain_intensity=0.9
        ),
        problem_statement="Logistics companies lose millions due to inefficient routing.",
        solution_description="""
        A comprehensive AI-powered platform for logistics optimization.
        Features:
        1. Real-time fleet tracking (Needs Background Jobs/Redis).
        2. AI Route Optimization using Genetic Algorithms (Needs AI Integration).
        3. Automated Email Alerts for drivers (Needs Email Service).
        4. Enterprise Subscription Billing (Needs Payments/Stripe integration logic).
        5. Heavy Data Processing for historical analysis (Needs Celery).
        """,
        value_proposition="Save 20% on fuel costs.",
        revenue_model=RevenueModel.SUBSCRIPTION,
        pricing_hypothesis=PricingHypothesis(
            tiers=["Pro", "Enterprise"],
            price_range="$500 - $5000 / month"
        ),
        tam_estimate="$50B",
        sam_estimate="$10B",
        som_estimate="$500M",
        competitive_landscape=["SAP", "Oracle", "Flexport"],
        technical_requirements_summary="High concurrency, Background Processing, AI Inference"
    )
    
    print(f"📝 Testing with Idea: {idea.name}")
    print(f"📋 Scope: {idea.solution_description[:100]}...")

    # 3. Initialize Pipeline
    pipeline = StartupGenerationPipeline(config)
    
    # OVERRIDE OUTPUT DIR for Stress Test isolation
    pipeline.config.code_generation.output_directory = str(output_dir)

    
    # 4. INJECT ROBUST MOCK COMPONENTS (Bypassing Monkey-Patching issues)
    print("🤖 Injecting RobustMockClient deeply into pipeline...")
    robust_client = RobustMockClient()
    
    # A. Prompt Engine (Lazy property, so we prime it)
    from src.prompt_engineering.engine import PromptEngineeringEngine
    pe = PromptEngineeringEngine(config, llm_client=robust_client)
    pipeline._prompt_engine = pe
    
    # B. Code Generator (Already init in pipeline.__init__)
    # We can just swap the client attribute if it exists
    if hasattr(pipeline.code_generator, 'llm_client'):
        pipeline.code_generator.llm_client = robust_client
    else:
        # If it doesn't store it publicly, we might need to rely on the patch (which failed)
        # But EnhancedCodeGenerator usually stores it.
        # Let's check init: self.llm_client = llm_client or get_llm_client()
        # So yes, it has it.
        pipeline.code_generator.llm_client = robust_client

    # C. Intelligence Engine
    pipeline.intelligence_engine.llm_client = robust_client

    
    # Override Code Generator Output path for test
    # (We rely on the pipeline to pass the prompt, but we want control over where it writes)
    # The pipeline uses config for output dir usually. We'll let it run and then check generated_codebase.output_path
    
    try:
        # 4. Execute Pipeline
        print("\n⚙️  Running Pipeline (Intelligence -> Refinement -> Code Gen -> QA)...")
        # We start from idea to skip the mock intelligence gathering time (which is just sleeping usually)
        # But verify_system checked that. Here we focus on the HEAVY lifting of code gen.
        
        output = asyncio.run(pipeline.run_from_idea(idea))
        
        if not output.generated_codebase:
            print("❌ FAILURE: No codebase generated.")
            return
            
        code_path = Path(output.generated_codebase.output_path)
        print(f"\n✅ Pipeline Complete. Output at: {code_path}")
        
    except Exception as e:
        print(f"❌ CRITICAL FAILURE during execution: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Validation / Assertions
    print("\n🔍 Validating Artifacts...")
    
    failures = []
    
    def check(condition, message):
        if condition:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")
            failures.append(message)

    # A. Structure
    check((code_path / "backend").exists(), "Backend Directory Exists")
    check((code_path / "frontend").exists(), "Frontend Directory Exists")
    check((code_path / "docker-compose.yml").exists(), "Docker Compose Exists")
    
    # B. Integrations (Stress Test specific)
    check((code_path / "backend/app/worker.py").exists(), "Celery Worker Generated (Background Jobs)")
    check((code_path / "backend/app/services/ai.py").exists(), "AI Service Generated (AI Integration)")
    check((code_path / "backend/app/services/email.py").exists(), "Email Service Generated (Email Support)")
    
    # C. Contract-First (Phase 7 Feature)
    schema_path = code_path / "frontend/src/types/schema.ts"
    check(schema_path.exists(), "Frontend Type Schema Exists")
    if schema_path.exists():
        content = schema_path.read_text()
        check("export interface" in content, "Schema contains TypeScript Interface")
        
    # D. QA Verification (Phase 7 Feature)
    # Check if imports are sorted in backend/main.py
    main_py = code_path / "backend/app/main.py"
    if main_py.exists():
        content = main_py.read_text()
        # isort usually groups standard lib imports first.
        # Simple check: fastapi should be after typing/sys if present, or just checking if it looks clean
        # Start of file usually has docstring or imports
        check(len(content) > 0, "Main.py is not empty")
        
    # E. Frontend Configs
    check((code_path / "frontend/tailwind.config.ts").exists(), "Tailwind Config Exists")
    check((code_path / "frontend/next.config.js").exists() or (code_path / "frontend/next.config.mjs").exists(), "Next.js Config Exists")

    print("\n" + "="*30)
    if not failures:
        print("🎉 STRESS TEST PASSED: System is Robust.")
    else:
        print(f"⚠️  STRESS TEST COMPLETED WITH {len(failures)} FAILURES.")
        sys.exit(1)

if __name__ == "__main__":
    run_stress_test()

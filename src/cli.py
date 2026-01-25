"""
Command-line interface for the Startup Generator.
"""

import asyncio
import json
from pathlib import Path

import click
from loguru import logger

from .config import load_config
from .models import BuyerPersona, PricingHypothesis, RevenueModel, StartupIdea
from .pipeline import StartupGenerationPipeline
from .utils.ui import UI
from .deployment.engine import DeploymentEngine
from .deployment.models import DeploymentConfig, DeploymentProviderType, DeploymentEnvironment


@click.group()
def cli():
    """Automated Startup Generation Pipeline"""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    default="config.yml",
    help="Path to configuration file",
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    "-o",
    default="./output",
    help="Output directory for results",
)
@click.option(
    "--demo",
    is_flag=True,
    help="Run in demo mode with sample data (no API calls)",
)
@click.option(
    "--skip-refinement",
    is_flag=True,
    help="Skip prompt refinement step",
)
@click.option(
    "--skip-code-gen",
    is_flag=True,
    help="Skip code generation step",
)
@click.option(
    "--llm-provider",
    type=click.Choice(['auto', 'perplexity', 'gemini', 'groq', 'openrouter', 'openai', 'anthropic', 'mock', 'multi']),
    default='auto',
    help="LLM provider to use (perplexity has real-time web search, auto tries providers in order, multi uses failover)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output with detailed logging",
)
@click.option(
    "--deploy",
    is_flag=True,
    help="Deploy immediately after generation",
)
@click.option(
    "--theme",
    "-t",
    type=click.Choice(['Modern', 'Minimalist', 'Cyberpunk', 'Corporate'], case_sensitive=False),
    default='Modern',
    help="UI theme for the generated app",
)
def generate(config, output, demo, skip_refinement, skip_code_gen, llm_provider, verbose, deploy, theme):
    """Run the full pipeline once."""
    UI.header("Startup Generator", "Full Pipeline Execution")
    
    if demo:
        UI.warning("MODE: Demo (using sample data)")
    if llm_provider == 'mock':
        UI.warning("LLM: Mock (no real API calls)")
    UI.info(f"Theme: [bold]{theme}[/]")

    try:
        # Load configuration
        UI.step(f"Loading configuration from: {config}")
        pipeline_config = load_config(config)

        # Create pipeline with LLM provider
        pipeline = StartupGenerationPipeline(pipeline_config, llm_provider=llm_provider)

        # Run pipeline
        UI.step("Starting pipeline execution...")
        
        # Use progress bar for generation (mocking steps since pipeline handles internal logic)
        # Ideally pipeline would yield progress, but for now we wrap the async run
        with UI.spinner("Running pipeline..."):
             result = asyncio.run(pipeline.run(
                demo_mode=demo,
                skip_refinement=skip_refinement,
                skip_code_gen=skip_code_gen,
                output_dir=output,
                theme=theme
            ))

        # Display results
        UI.header("Results")

        if result.selected_idea:
            UI.info(f"Idea: [bold]{result.selected_idea.name}[/]")
            print(f"   {result.selected_idea.one_liner}")

        if result.evaluation:
            top_eval = result.evaluation.evaluated_ideas[0]
            UI.info(f"Total Score: [bold green]{top_eval.total_score:.2f}[/]")

        if result.generated_codebase:
            UI.success(f"Codebase Generated at: {result.generated_codebase.output_path}")
            UI.info(f"Files: {result.generated_codebase.files_generated}")

        UI.success("Pipeline completed successfully!")

        # Trigger deployment if requested
        if deploy and result.generated_codebase:
             UI.step("Initiating Post-Generation Deployment...")
             ctx = click.get_current_context()
             ctx.invoke(
                 globals()['deploy'], 
                 codebase_path=result.generated_codebase.output_path,
                 frontend="vercel",
                 backend="render",
                 env="production"
             )

    except Exception as e:
        UI.error(f"Pipeline failed: {e}")
        logger.exception("Pipeline execution failed")
        raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    default="config.yml",
    help="Path to configuration file",
    type=click.Path(exists=True),
)
@click.option(
    "--schedule",
    "-s",
    default="0 6 * * *",
    help="Cron expression for scheduling",
)
def daemon(config, schedule):
    """Run pipeline on a schedule (daemon mode)."""
    click.echo("=" * 80)
    click.echo("Startup Generator - Daemon Mode")
    click.echo("=" * 80)
    click.echo(f"\nSchedule: {schedule}")
    click.echo("Press Ctrl+C to stop\n")

    try:
        from .pipeline import run_on_schedule

        pipeline_config = load_config(config)
        run_on_schedule(pipeline_config, schedule)

    except KeyboardInterrupt:
        click.echo("\n\nDaemon stopped by user")
    except Exception as e:
        click.secho(f"\n✗ Daemon failed: {e}", fg="red", bold=True)
        raise click.Abort()


@cli.command()
@click.argument("idea_file", type=click.Path(exists=True))
@click.option(
    "--config",
    "-c",
    default="config.yml",
    help="Path to configuration file",
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    "-o",
    default="./output",
    help="Output directory",
)
def build_from_idea(idea_file, config, output):
    """Skip intelligence gathering, build from existing idea JSON file."""
    click.echo("=" * 80)
    click.echo("Startup Generator - Build from Existing Idea")
    click.echo("=" * 80)

    try:
        # Load idea from file
        click.echo(f"\nLoading idea from: {idea_file}")
        with open(idea_file, encoding='utf-8') as f:
            idea_data = json.load(f)

        # Convert to StartupIdea object
        idea = StartupIdea(**idea_data)

        # Load configuration
        pipeline_config = load_config(config)

        # Create and run pipeline
        pipeline = StartupGenerationPipeline(pipeline_config)

        click.echo(f"\nBuilding product for: {idea.name}\n")
        result = asyncio.run(pipeline.run_from_idea(idea))

        # Display results
        click.echo("\n" + "=" * 80)
        click.echo("RESULTS")
        click.echo("=" * 80)

        if result.generated_codebase:
            click.echo(f"\nCodebase: {result.generated_codebase.output_path}")
            click.echo(f"Files: {result.generated_codebase.files_generated}")
            click.echo(f"Lines: {result.generated_codebase.lines_of_code}")

        click.echo("\n" + "=" * 80)
        click.secho("✓ Build completed successfully!", fg="green", bold=True)
        click.echo("=" * 80)

    except Exception as e:
        click.secho(f"\n✗ Build failed: {e}", fg="red", bold=True)
        logger.exception("Build from idea failed")
        raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    default="config.yml",
    help="Path to configuration file",
    type=click.Path(exists=True),
)
def test_intelligence(config):
    """Test intelligence gathering only (no code generation)."""
    click.echo("Testing intelligence gathering...")

    try:
        from .intelligence import IntelligenceGatheringEngine

        pipeline_config = load_config(config)
        engine = IntelligenceGatheringEngine(pipeline_config)

        intelligence = asyncio.run(engine.gather())

        click.echo(f"\nPain Points: {len(intelligence.pain_points)}")
        click.echo(f"Emerging Industries: {len(intelligence.emerging_industries)}")
        click.echo(f"Opportunities: {len(intelligence.opportunity_categories)}")

        if intelligence.pain_points:
            click.echo("\nTop 5 Pain Points:")
            for i, pp in enumerate(intelligence.pain_points[:5], 1):
                click.echo(f"{i}. {pp.description[:100]}...")

        click.secho("\n✓ Intelligence gathering test completed!", fg="green")

    except Exception as e:
        click.secho(f"\n✗ Test failed: {e}", fg="red", bold=True)
        raise click.Abort()


@cli.command()
def list_providers():
    """List available LLM providers."""
    from src.llm import list_available_providers
    
    available = list_available_providers()
    
    provider_info = {
        "gemini": {"model": "gemini-1.5-flash", "desc": "Google AI Studio - 1,500 req/day"},
        "groq": {"model": "llama-3.1-70b-versatile", "desc": "Groq Cloud - 14,400 req/day, very fast"},
        "openrouter": {"model": "llama-3.1-8b-instruct:free", "desc": "OpenRouter - Multiple free models"},
        "openai": {"model": "gpt-4-turbo-preview", "desc": "OpenAI - Paid only"},
        "anthropic": {"model": "claude-sonnet-4-20250514", "desc": "Anthropic - Paid only"},
        "mock": {"model": "mock-model", "desc": "Testing mode - no API calls"}
    }
    
    rows = []
    for provider, is_available in available.items():
        status = "[green]✓ Ready[/]" if is_available else "[red]✗ No API key[/]"
        info = provider_info.get(provider, {})
        model = info.get("model", "")
        desc = info.get("desc", "")
        rows.append([status, provider, model, desc])
    
    UI.table("Available LLM Providers", ["Status", "Provider", "Model", "Description"], rows)
    UI.info("\nUse [bold]--llm-provider <name>[/] to select a provider")


@cli.command()
@click.option('--provider', '-p', default='auto', help='Provider to test (or "all")')
def test_llm(provider):
    """Test LLM provider connectivity."""
    from src.llm import get_llm_client, list_available_providers
    
    if provider == "all":
        providers_to_test = [p for p, available in list_available_providers().items() if available and p != "mock"]
    else:
        providers_to_test = [provider]
    
    for prov in providers_to_test:
        UI.step(f"Testing {prov}...")
        try:
            with UI.spinner(f"Connecting to {prov}..."):
                client = get_llm_client(prov)
                response = client.complete("Say 'Hello!'", max_tokens=10)
            
            UI.success(f"{prov}: [italic]{response.content.strip()}[/]")
            UI.info(f"  Model: {response.model}, Latency: {response.latency_ms:.0f}ms")
        except Exception as e:
            UI.error(f"{prov}: {e}")


@cli.command()
@click.argument("codebase_path", type=click.Path(exists=True))
@click.option("--frontend", default="vercel", help="Frontend provider (vercel)")
@click.option("--backend", default="render", help="Backend provider (render, railway, fly_io)")
@click.option("--env", default="production", help="Target environment")
def deploy(codebase_path, frontend, backend, env):
    """Deploy the application to cloud providers."""
    
    # Delayed import to avoid circular dependencies if any
    from .deployment.engine import DeploymentEngine
    from .deployment.models import DeploymentConfig, DeploymentProviderType, DeploymentEnvironment
    
    UI.header("Deploying App", f"From: {codebase_path}")
    
    try:
        engine = DeploymentEngine()
        
        # Deploy Frontend
        UI.step(f"[1/2] Deploying Frontend to {frontend.upper()}...")
        fe_config = DeploymentConfig(
            provider=DeploymentProviderType(frontend),
            environment=DeploymentEnvironment(env)
        )
        # Mock secrets for now
        secrets = {"VERCEL_TOKEN": "mock", "RENDER_API_KEY": "mock"}
        
        # We need to target the frontend dir specifically for Vercel
        fe_path = Path(codebase_path) / "frontend"
        
        # Run async deploy in sync CLI
        with UI.spinner("Deploying frontend..."):
            fe_result = asyncio.run(engine.deploy(fe_path, fe_config, secrets))
        
        if fe_result.success:
            UI.success(f"Frontend Deployed: {fe_result.frontend_url}")
        else:
            UI.error(f"Frontend Failed: {fe_result.error_message}")
            
        # Deploy Backend
        UI.step(f"[2/2] Deploying Backend to {backend.upper()}...")
        be_config = DeploymentConfig(
            provider=DeploymentProviderType(backend),
            environment=DeploymentEnvironment(env)
        )
        be_path = Path(codebase_path) # Render deploy usually takes root
        
        with UI.spinner("Deploying backend..."):
            be_result = asyncio.run(engine.deploy(be_path, be_config, secrets))
        
        if be_result.success:
            UI.success(f"Backend Deployed: {be_result.backend_url}")
        else:
            UI.error(f"Backend Failed: {be_result.error_message}")

    except Exception as e:
        UI.error(f"Deployment Error: {e}")


@cli.command()
@click.argument("deployment_id")
@click.argument("to_id")
def rollback(deployment_id, to_id):
    """Rollback a deployment to a previous version."""
    click.echo(f"Rolling back {deployment_id} to {to_id}...")
    # engine = DeploymentEngine()
    # success = asyncio.run(engine.rollback(deployment_id, to_id))
    click.echo("✓ Rollback initiated (Mock)")


@cli.command()
@click.argument("codebase_path", type=click.Path(exists=True))
def estimate_cost(codebase_path):
    """Estimate monthly infrastructure costs."""
    from .deployment.infrastructure.cost_estimator import CostEstimator
    from .deployment.models import DeploymentConfig, DeploymentProviderType
    
    estimator = CostEstimator()
    # Estimate for Vercel + Render
    v_conf = DeploymentConfig(provider=DeploymentProviderType.VERCEL)
    r_conf = DeploymentConfig(provider=DeploymentProviderType.RENDER)
    
    est_v = estimator.estimate(v_conf)
    est_r = estimator.estimate(r_conf)
    
    total = est_v.total_monthly + est_r.total_monthly
    
    click.echo("\nMonthly Cost Estimate:")
    click.echo("-" * 30)
    click.echo(f"Frontend (Vercel): ${est_v.total_monthly:.2f}")
    click.echo(f"Backend (Render):  ${est_r.total_monthly:.2f}")
    click.echo("-" * 30)
    click.echo(f"TOTAL:             ${total:.2f}")


@cli.command()
def version():
    """Show version information."""
    from . import __version__

    click.echo(f"Startup Generator v{__version__}")


@cli.command()
def wizard():
    """Interactive Startup Builder Wizard."""
    from src.llm import get_llm_client
    
    UI.header("Startup Builder Wizard", "Interactive Mode")
    
    # 1. Choose Mode
    mode = UI.prompt("Choose mode ([1] Automated Discovery, [2] Build Specific Idea)", default="1")
    
    if mode == "2":
        # Specific Idea Mode
        name = UI.prompt("What is the name of your startup?")
        desc = UI.prompt("Describe your startup solution:")
        
        UI.step("Analyzing idea and generating full profile...")
        
        try:
            with UI.spinner(" expanding idea with AI..."):
                client = get_llm_client("auto")
                prompt = f"""
                Expand this startup idea into a full JSON profile matching the StartupIdea model.
                Name: {name}
                Description: {desc}
                
                Return JSON with fields:
                - name
                - one_liner (max 100 chars)
                - problem_statement
                - solution_description
                - target_buyer_persona {{ title, company_size, industry, budget_authority, pain_intensity }}
                - value_proposition
                - revenue_model (subscription, usage, transaction, hybrid)
                - pricing_hypothesis {{ tiers, price_range }}
                - tam_estimate
                - sam_estimate
                - som_estimate
                - competitive_landscape (list of strings)
                - differentiation_factors (list of strings)
                - automation_opportunities (list of strings)
                - technical_requirements_summary
                
                Output ONLY valid JSON.
                """
                
                response = client.complete(prompt, json_mode=True)
                idea_data = json.loads(response.content.replace('```json', '').replace('```', '').strip())
                idea = StartupIdea(**idea_data)
                
            UI.success(f"Idea Profile Created: {idea.name}")
            print(f"   {idea.one_liner}")
            
            # Select theme
            theme_choice = UI.prompt("Choose theme ([1] Modern, [2] Minimalist, [3] Cyberpunk, [4] Corporate)", default="1")
            theme_map = {"1": "Modern", "2": "Minimalist", "3": "Cyberpunk", "4": "Corporate"}
            theme = theme_map.get(theme_choice, "Modern")
            UI.info(f"Selected theme: [bold]{theme}[/]")
            
            # Confirm
            if not UI.confirm("Proceed with generation?"):
                UI.warning("Aborted.")
                return
                
            # Run Pipeline from Idea
            # Re-use config logic
            pipeline_config = load_config("config.yml")
            pipeline = StartupGenerationPipeline(pipeline_config)
            
            UI.step("Building codebase...")
            result = asyncio.run(pipeline.run_from_idea(idea, theme=theme))
            
            if result.generated_codebase:
                UI.success(f"Codebase ready at: {result.generated_codebase.output_path}")
                
                if UI.confirm("Deploy now?"):
                    UI.step("Deploying...")
                    # Call deploy logic (simplified)
                    ctx = click.get_current_context()
                    ctx.invoke(
                         globals()['deploy'], 
                         codebase_path=result.generated_codebase.output_path,
                         frontend="vercel",
                         backend="render",
                         env="production"
                     )

        except Exception as e:
            UI.error(f"Failed to process idea: {e}")
            logger.exception("Wizard failed")

    else:
        # Automated Mode - prompt for theme
        theme_choice = UI.prompt("Choose theme ([1] Modern, [2] Minimalist, [3] Cyberpunk, [4] Corporate)", default="1")
        theme_map = {"1": "Modern", "2": "Minimalist", "3": "Cyberpunk", "4": "Corporate"}
        theme = theme_map.get(theme_choice, "Modern")
        
        UI.info("Running Automated Discovery Pipeline...")
        ctx = click.get_current_context()
        ctx.invoke(generate, config="config.yml", deploy=False, theme=theme)


if __name__ == "__main__":
    cli()

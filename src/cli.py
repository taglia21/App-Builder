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
    type=click.Choice(['auto', 'gemini', 'groq', 'openrouter', 'openai', 'anthropic', 'mock', 'multi']),
    default='auto',
    help="LLM provider to use (auto tries providers in order, multi uses failover)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output with detailed logging",
)
def generate(config, output, demo, skip_refinement, skip_code_gen, llm_provider, verbose):
    """Run the full pipeline once."""
    click.echo("=" * 80)
    click.echo("Startup Generator - Full Pipeline Execution")
    if demo:
        click.echo("MODE: Demo (using sample data)")
    if llm_provider == 'mock':
        click.echo("LLM: Mock (no real API calls)")
    click.echo("=" * 80)

    try:
        # Load configuration
        click.echo(f"\nLoading configuration from: {config}")
        pipeline_config = load_config(config)

        # Create pipeline with LLM provider
        pipeline = StartupGenerationPipeline(pipeline_config, llm_provider=llm_provider)

        # Run pipeline
        click.echo("\nStarting pipeline execution...\n")
        result = asyncio.run(pipeline.run(
            demo_mode=demo,
            skip_refinement=skip_refinement,
            skip_code_gen=skip_code_gen,
            output_dir=output
        ))

        # Display results
        click.echo("\n" + "=" * 80)
        click.echo("RESULTS")
        click.echo("=" * 80)

        if result.selected_idea:
            click.echo(f"\nIdea: {result.selected_idea.name}")
            click.echo(f"One-liner: {result.selected_idea.one_liner}")

        if result.evaluation:
            top_eval = result.evaluation.evaluated_ideas[0]
            click.echo(f"\nTotal Score: {top_eval.total_score:.2f}")

        if result.generated_codebase:
            click.echo(f"\nCodebase: {result.generated_codebase.output_path}")
            click.echo(f"Files: {result.generated_codebase.files_generated}")

        click.echo("\n" + "=" * 80)
        click.secho("✓ Pipeline completed successfully!", fg="green", bold=True)
        click.echo("=" * 80)

    except Exception as e:
        click.secho(f"\n✗ Pipeline failed: {e}", fg="red", bold=True)
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
        with open(idea_file) as f:
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
    
    click.echo("\n" + "="*60)
    click.echo("Available LLM Providers")
    click.echo("="*60 + "\n")
    
    available = list_available_providers()
    
    provider_info = {
        "gemini": {"model": "gemini-1.5-flash", "desc": "Google AI Studio - 1,500 req/day"},
        "groq": {"model": "llama-3.1-70b-versatile", "desc": "Groq Cloud - 14,400 req/day, very fast"},
        "openrouter": {"model": "llama-3.1-8b-instruct:free", "desc": "OpenRouter - Multiple free models"},
        "openai": {"model": "gpt-4-turbo-preview", "desc": "OpenAI - Paid only"},
        "anthropic": {"model": "claude-sonnet-4-20250514", "desc": "Anthropic - Paid only"},
        "mock": {"model": "mock-model", "desc": "Testing mode - no API calls"}
    }
    
    for provider, is_available in available.items():
        status = "✓ Ready" if is_available else "✗ No API key"
        info = provider_info.get(provider, {})
        model = info.get("model", "")
        desc = info.get("desc", "")
        
        click.echo(f"{status:15} {provider:15} {model:30} {desc}")
    
    click.echo("\nUse --llm-provider <name> to select a provider")


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
        click.echo(f"\nTesting {prov}...")
        try:
            client = get_llm_client(prov)
            response = client.complete("Say 'Hello, I am working!' in exactly those words.", max_tokens=50)
            click.echo(f"✓ {prov}: {response.content[:50]}")
            click.echo(f"  Model: {response.model}, Latency: {response.latency_ms:.0f}ms")
        except Exception as e:
            click.echo(f"✗ {prov}: {e}")


@cli.command()
def version():
    """Show version information."""
    from . import __version__

    click.echo(f"Startup Generator v{__version__}")


if __name__ == "__main__":
    cli()

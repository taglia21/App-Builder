# -*- coding: utf-8 -*-
"""
LaunchForge Interactive AI Assistant

The killer feature - users describe their startup idea in plain English
and get working, production-ready code in minutes.

This module provides an interactive conversational interface that:
1. Welcomes users and asks them to describe their app idea
2. Uses Perplexity to validate and research the market
3. Asks intelligent follow-up questions
4. Converts ideas into proper format for code generation
5. Generates the complete application
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from .llm import get_llm_client, list_available_providers
from .llm.client import BaseLLMClient
from .models import (
    StartupIdea,
    BuyerPersona,
    PricingHypothesis,
    RevenueModel,
)
from .config import load_config
from .pipeline import StartupGenerationPipeline
from .branding import LOGO_ASCII, TAGLINE, VERSION
from .utils.ui import UI


# ============================================================================
# Assistant Configuration
# ============================================================================

@dataclass
class ConversationContext:
    """Tracks conversation state and gathered information."""
    session_id: str = field(default_factory=lambda: str(uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    # User's raw idea
    raw_idea: str = ""
    
    # Validated/researched information
    market_validation: Dict[str, Any] = field(default_factory=dict)
    
    # Follow-up responses
    target_users: str = ""
    key_features: List[str] = field(default_factory=list)
    monetization: str = ""
    unique_value: str = ""
    
    # Generated startup idea
    startup_idea: Optional[StartupIdea] = None
    
    # Output path
    output_path: str = ""
    
    def is_complete(self) -> bool:
        """Check if we have enough info to generate."""
        return bool(
            self.raw_idea and 
            self.target_users and 
            self.key_features and 
            self.monetization
        )


class InteractiveAssistant:
    """
    Interactive AI assistant that guides users through idea-to-app journey.
    
    The assistant uses a conversational flow:
    1. Welcome & Idea Capture
    2. Market Research & Validation (via Perplexity)
    3. Follow-up Questions
    4. Idea Refinement
    5. Code Generation
    """
    
    def __init__(
        self,
        llm_provider: str = "auto",
        output_dir: str = "./output",
        theme: str = "Modern",
        verbose: bool = False,
    ):
        self.console = Console()
        self.llm_provider = llm_provider
        self.output_dir = output_dir
        self.theme = theme
        self.verbose = verbose
        
        # Initialize LLM client
        self._llm_client: Optional[BaseLLMClient] = None
        
        # Conversation context
        self.context = ConversationContext()
    
    @property
    def llm_client(self) -> BaseLLMClient:
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client(self.llm_provider)
        return self._llm_client
    
    def _print_welcome(self):
        """Print welcome banner and introduction."""
        self.console.print()
        self.console.print(f"[bold cyan]{LOGO_ASCII}[/bold cyan]")
        self.console.print(f"[dim]{TAGLINE} • v{VERSION}[/dim]")
        self.console.print()
        
        welcome_text = """
[bold white]Welcome to LaunchForge Build Mode![/bold white]

I'm your AI startup builder. Describe your app idea in plain English, 
and I'll help you:

  🔍  [cyan]Validate[/cyan] your idea with real-time market research
  💡  [cyan]Refine[/cyan] your concept with targeted questions  
  ⚡  [cyan]Generate[/cyan] a complete, production-ready codebase
  🚀  [cyan]Deploy[/cyan] to the cloud with one command

[dim]Powered by Perplexity AI for real-time web intelligence[/dim]
"""
        self.console.print(Panel(welcome_text, border_style="cyan", title="🚀 Build Mode", subtitle="[dim]Type 'quit' to exit[/dim]"))
        self.console.print()
    
    def _print_section(self, title: str, icon: str = "➤"):
        """Print a section header."""
        self.console.print()
        self.console.print(f"[bold cyan]{icon} {title}[/bold cyan]")
        self.console.print("[dim]" + "─" * 50 + "[/dim]")
    
    def _prompt(self, question: str, multiline: bool = False) -> str:
        """Get user input with rich formatting."""
        self.console.print()
        self.console.print(f"[bold yellow]?[/bold yellow] [bold]{question}[/bold]")
        
        if multiline:
            self.console.print("[dim]  (Press Enter twice when done)[/dim]")
            lines = []
            empty_count = 0
            while empty_count < 1:
                try:
                    line = input("  ")
                    if line == "":
                        empty_count += 1
                    else:
                        empty_count = 0
                        lines.append(line)
                except EOFError:
                    break
            return "\n".join(lines).strip()
        else:
            try:
                response = input("  → ")
                return response.strip()
            except EOFError:
                return ""
    
    def _confirm(self, question: str, default: bool = True) -> bool:
        """Ask for confirmation."""
        default_str = "[Y/n]" if default else "[y/N]"
        response = self._prompt(f"{question} {default_str}")
        
        if not response:
            return default
        return response.lower() in ("y", "yes", "yeah", "yep", "1", "true")
    
    def _select(self, question: str, options: List[str]) -> int:
        """Present options and get selection."""
        self.console.print()
        self.console.print(f"[bold yellow]?[/bold yellow] [bold]{question}[/bold]")
        
        for i, option in enumerate(options, 1):
            self.console.print(f"    [cyan]{i}[/cyan]. {option}")
        
        while True:
            try:
                response = input("  → Enter number: ").strip()
                if response.lower() in ("q", "quit", "exit"):
                    return -1
                idx = int(response) - 1
                if 0 <= idx < len(options):
                    return idx
                self.console.print(f"  [red]Please enter 1-{len(options)}[/red]")
            except ValueError:
                self.console.print("  [red]Please enter a number[/red]")
            except EOFError:
                return 0
    
    def _spinner_context(self, message: str):
        """Create a spinner context manager."""
        return self.console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots")
    
    # =========================================================================
    # Step 1: Capture the Idea
    # =========================================================================
    
    def capture_idea(self) -> bool:
        """Get the user's startup idea."""
        self._print_section("Step 1: Tell Me Your Idea", "💡")
        
        self.console.print("""
[white]Describe your startup or app idea. Be as detailed as you like!

What problem are you solving? What does your app do?[/white]
""")
        
        idea = self._prompt(
            "Describe your startup idea:",
            multiline=True
        )
        
        if not idea or idea.lower() in ("quit", "exit", "q"):
            return False
        
        self.context.raw_idea = idea
        
        self.console.print()
        self.console.print(f"[green]✓ Got it![/green] Let me research your idea...")
        
        return True
    
    # =========================================================================
    # Step 2: Market Research & Validation
    # =========================================================================
    
    def validate_market(self) -> bool:
        """Use Perplexity to validate and research the market."""
        self._print_section("Step 2: Market Research", "🔍")
        
        with self._spinner_context("Researching market with real-time web intelligence..."):
            try:
                research_prompt = f"""
You are a startup analyst. Research this startup idea and provide market intelligence.

STARTUP IDEA:
{self.context.raw_idea}

Analyze and provide:
1. **Market Opportunity**: Is there a real market for this? Estimated TAM/SAM/SOM
2. **Problem Validation**: Is this a significant pain point people have?
3. **Competitive Landscape**: Who are the main competitors? What are their weaknesses?
4. **Unique Angle**: What could make this stand out?
5. **Technical Feasibility**: How complex is this to build?
6. **Monetization Potential**: What business models would work?
7. **Red Flags**: Any concerns or risks?

Be concise and actionable. Use current data from the web.
"""
                
                response = self.llm_client.complete(
                    research_prompt,
                    system_prompt="You are an expert startup analyst with access to real-time market data.",
                    max_tokens=2000,
                    temperature=0.7
                )
                
                self.context.market_validation = {
                    "research": response.content,
                    "model": response.model,
                    "provider": response.provider,
                }
                
            except Exception as e:
                logger.error(f"Market research failed: {e}")
                self.console.print(f"[yellow]⚠ Could not complete full research: {e}[/yellow]")
                self.console.print("[dim]Continuing with available information...[/dim]")
                self.context.market_validation = {"research": "Research unavailable", "error": str(e)}
        
        # Display research results
        self.console.print()
        self.console.print(Panel(
            Markdown(self.context.market_validation.get("research", "Research unavailable")),
            title="[bold cyan]📊 Market Research Results[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))
        
        # Ask if they want to proceed
        self.console.print()
        if not self._confirm("Does this look promising? Continue building?"):
            self.console.print("[yellow]No worries! Feel free to refine your idea.[/yellow]")
            return False
        
        return True
    
    # =========================================================================
    # Step 3: Follow-up Questions
    # =========================================================================
    
    def ask_followups(self) -> bool:
        """Ask targeted follow-up questions."""
        self._print_section("Step 3: Let's Refine Your Idea", "💬")
        
        self.console.print("""
[white]A few quick questions to make your app even better...[/white]
""")
        
        # Target Users
        target = self._prompt(
            "Who is your target user? (e.g., 'small business owners', 'remote teams', 'fitness enthusiasts')"
        )
        if target.lower() in ("quit", "exit", "q"):
            return False
        self.context.target_users = target or "General consumers"
        
        # Key Features
        features_input = self._prompt(
            "What are the 3-5 key features? (comma-separated)"
        )
        if features_input.lower() in ("quit", "exit", "q"):
            return False
        self.context.key_features = [
            f.strip() for f in features_input.split(",") if f.strip()
        ] or ["Core functionality", "User dashboard", "Analytics"]
        
        # Monetization
        monetization_options = [
            "Subscription (monthly/annual)",
            "Usage-based (pay per use)",
            "Transaction fees (% of transactions)",
            "Freemium (free + premium)",
            "Not sure yet"
        ]
        mon_idx = self._select("How do you plan to make money?", monetization_options)
        if mon_idx == -1:
            return False
        self.context.monetization = monetization_options[mon_idx]
        
        # Unique Value
        unique = self._prompt(
            "What makes your solution unique? (your secret sauce)"
        )
        if unique.lower() in ("quit", "exit", "q"):
            return False
        self.context.unique_value = unique or "Innovative approach to the problem"
        
        self.console.print()
        self.console.print("[green]✓ Perfect![/green] I have everything I need.")
        
        return True
    
    # =========================================================================
    # Step 4: Generate Startup Idea Model
    # =========================================================================
    
    def generate_idea_model(self) -> bool:
        """Convert gathered info into a proper StartupIdea model."""
        self._print_section("Step 4: Creating Your Startup Profile", "⚡")
        
        with self._spinner_context("Synthesizing your startup profile..."):
            try:
                synthesis_prompt = f"""
Convert this startup concept into a complete startup profile JSON.

RAW IDEA:
{self.context.raw_idea}

TARGET USERS: {self.context.target_users}

KEY FEATURES:
{json.dumps(self.context.key_features)}

MONETIZATION: {self.context.monetization}

UNIQUE VALUE: {self.context.unique_value}

MARKET RESEARCH:
{self.context.market_validation.get('research', 'N/A')[:1500]}

Generate a JSON object with these EXACT fields:
{{
  "name": "catchy startup name (2-3 words)",
  "one_liner": "compelling one-line description under 100 chars",
  "problem_statement": "clear problem being solved",
  "solution_description": "how the product solves it",
  "target_buyer_persona": {{
    "title": "job title or persona name",
    "company_size": "individual/small/medium/enterprise",
    "industry": "target industry",
    "budget_authority": true/false,
    "pain_intensity": 0.8
  }},
  "value_proposition": "why users should choose this",
  "revenue_model": "subscription|usage|transaction|hybrid",
  "pricing_hypothesis": {{
    "tiers": ["Free", "Pro $29/mo", "Enterprise custom"],
    "price_range": "$0-$299/mo"
  }},
  "tam_estimate": "Total Addressable Market estimate",
  "sam_estimate": "Serviceable Addressable Market",
  "som_estimate": "Serviceable Obtainable Market",
  "competitive_landscape": ["competitor 1", "competitor 2"],
  "differentiation_factors": ["factor 1", "factor 2"],
  "automation_opportunities": ["opportunity 1", "opportunity 2"],
  "technical_requirements_summary": "brief tech stack overview"
}}

Return ONLY valid JSON. Make it compelling and market-ready.
"""
                
                response = self.llm_client.complete(
                    synthesis_prompt,
                    system_prompt="You are an expert startup strategist. Generate accurate, compelling startup profiles.",
                    max_tokens=2000,
                    temperature=0.7,
                    json_mode=True
                )
                
                # Parse the JSON response
                content = response.content.strip()
                # Handle markdown code blocks
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                
                idea_data = json.loads(content)
                
                # Map revenue model string to enum
                rev_model_map = {
                    "subscription": RevenueModel.SUBSCRIPTION,
                    "usage": RevenueModel.USAGE,
                    "transaction": RevenueModel.TRANSACTION,
                    "hybrid": RevenueModel.HYBRID,
                }
                rev_str = idea_data.get("revenue_model", "subscription").lower()
                idea_data["revenue_model"] = rev_model_map.get(rev_str, RevenueModel.SUBSCRIPTION)
                
                # Create StartupIdea
                self.context.startup_idea = StartupIdea(**idea_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse idea JSON: {e}")
                self.console.print(f"[red]Error parsing AI response. Retrying...[/red]")
                # Fallback: create a basic idea
                self.context.startup_idea = self._create_fallback_idea()
            except Exception as e:
                logger.error(f"Failed to generate idea model: {e}")
                self.console.print(f"[yellow]⚠ Using simplified profile: {e}[/yellow]")
                self.context.startup_idea = self._create_fallback_idea()
        
        # Display the generated profile
        idea = self.context.startup_idea
        
        self.console.print()
        profile_table = Table(title=f"🚀 {idea.name}", show_header=False, border_style="cyan")
        profile_table.add_column("Field", style="cyan", width=20)
        profile_table.add_column("Value", style="white")
        
        profile_table.add_row("One-liner", idea.one_liner)
        profile_table.add_row("Problem", idea.problem_statement[:100] + "..." if len(idea.problem_statement) > 100 else idea.problem_statement)
        profile_table.add_row("Solution", idea.solution_description[:100] + "..." if len(idea.solution_description) > 100 else idea.solution_description)
        profile_table.add_row("Target", f"{idea.target_buyer_persona.title} @ {idea.target_buyer_persona.company_size}")
        profile_table.add_row("Revenue Model", idea.revenue_model.value.capitalize())
        profile_table.add_row("Pricing", idea.pricing_hypothesis.price_range)
        profile_table.add_row("TAM", idea.tam_estimate)
        
        self.console.print(profile_table)
        
        self.console.print()
        if not self._confirm("Does this capture your vision? Generate the app?"):
            self.console.print("[yellow]You can restart with 'nexusai build' to try again.[/yellow]")
            return False
        
        return True
    
    def _create_fallback_idea(self) -> StartupIdea:
        """Create a basic StartupIdea from context when AI parsing fails."""
        # Clean up the raw idea for naming
        name_words = self.context.raw_idea.split()[:3]
        name = " ".join(name_words).title() if name_words else "MyStartup"
        
        return StartupIdea(
            name=name + " App",
            one_liner=self.context.raw_idea[:97] + "..." if len(self.context.raw_idea) > 100 else self.context.raw_idea,
            problem_statement=f"Users struggle with: {self.context.raw_idea[:200]}",
            solution_description=f"A platform that {self.context.raw_idea[:200]}",
            target_buyer_persona=BuyerPersona(
                title=self.context.target_users or "End User",
                company_size="small",
                industry="Technology",
                budget_authority=True,
                pain_intensity=0.7
            ),
            value_proposition=self.context.unique_value or "Innovative solution to a real problem",
            revenue_model=RevenueModel.SUBSCRIPTION,
            pricing_hypothesis=PricingHypothesis(
                tiers=["Free", "Pro $19/mo", "Enterprise"],
                price_range="$0-$99/mo"
            ),
            tam_estimate="$1B+ market",
            sam_estimate="$100M serviceable",
            som_estimate="$10M obtainable",
            competitive_landscape=["Existing solutions", "Manual processes"],
            differentiation_factors=self.context.key_features[:3] if self.context.key_features else ["Unique approach"],
            automation_opportunities=["AI-powered automation", "Workflow optimization"],
            technical_requirements_summary="Modern web stack with FastAPI backend and Next.js frontend"
        )
    
    # =========================================================================
    # Step 5: Generate the Application
    # =========================================================================
    
    def generate_application(self) -> bool:
        """Generate the complete application."""
        self._print_section("Step 5: Building Your Application", "🔨")
        
        # Select theme
        themes = ["Modern", "Minimalist", "Cyberpunk", "Corporate"]
        theme_idx = self._select("Choose a UI theme:", themes)
        if theme_idx == -1:
            return False
        selected_theme = themes[theme_idx]
        
        idea = self.context.startup_idea
        
        # Create output directory
        safe_name = "".join(c if c.isalnum() else "_" for c in idea.name.lower())
        output_path = Path(self.output_dir) / f"{safe_name}_{self.context.session_id}"
        output_path.mkdir(parents=True, exist_ok=True)
        self.context.output_path = str(output_path)
        
        self.console.print()
        self.console.print(f"[cyan]Generating app for:[/cyan] [bold]{idea.name}[/bold]")
        self.console.print(f"[cyan]Theme:[/cyan] {selected_theme}")
        self.console.print(f"[cyan]Output:[/cyan] {output_path}")
        self.console.print()
        
        try:
            # Load config and run pipeline
            config = load_config("config.yml")
            pipeline = StartupGenerationPipeline(config, llm_provider=self.llm_provider)
            
            self.console.print("[dim]This may take a few minutes...[/dim]")
            self.console.print()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Generating codebase...", total=None)
                
                # Run the pipeline from the idea
                result = asyncio.run(
                    pipeline.run_from_idea(idea, output_dir=str(output_path), theme=selected_theme)
                )
            
            if result.generated_codebase:
                self._print_success(result.generated_codebase.output_path, result.generated_codebase.files_generated)
                return True
            else:
                self.console.print("[yellow]⚠ Code generation was skipped[/yellow]")
                return False
                
        except Exception as e:
            logger.exception("Code generation failed")
            self.console.print(f"[red]✗ Generation failed: {e}[/red]")
            return False
    
    def _print_success(self, output_path: str, files_count: int):
        """Print success message with next steps."""
        self.console.print()
        success_text = f"""
[bold green]✓ Your app is ready![/bold green]

[bold white]Generated:[/bold white]
  📁  {output_path}
  📄  {files_count} files created

[bold white]Quick Start:[/bold white]
  [cyan]cd {output_path}/backend[/cyan]
  [cyan]pip install -r requirements.txt[/cyan]
  [cyan]uvicorn main:app --reload[/cyan]

  Then visit: [underline cyan]http://localhost:8000/docs[/underline cyan]

[bold white]Deploy to Cloud:[/bold white]
  [cyan]nexusai deploy {output_path}[/cyan]

[dim]Your startup journey begins! 🚀[/dim]
"""
        self.console.print(Panel(success_text, border_style="green", title="🎉 Success!"))
    
    # =========================================================================
    # Main Run Loop
    # =========================================================================
    
    def run(self) -> bool:
        """Run the complete interactive assistant flow."""
        try:
            self._print_welcome()
            
            # Check LLM availability
            providers = list_available_providers()
            if not any(providers.values()):
                self.console.print("[red]No LLM providers available![/red]")
                self.console.print("[yellow]Set PERPLEXITY_API_KEY or GROQ_API_KEY[/yellow]")
                return False
            
            active_provider = next((p for p, v in providers.items() if v and p != "mock"), "mock")
            self.console.print(f"[dim]Using LLM: {active_provider}[/dim]")
            self.console.print()
            
            # Step 1: Capture idea
            if not self.capture_idea():
                self.console.print("\n[dim]Goodbye! Come back when inspiration strikes. 👋[/dim]")
                return False
            
            # Step 2: Market research
            if not self.validate_market():
                return False
            
            # Step 3: Follow-up questions
            if not self.ask_followups():
                return False
            
            # Step 4: Generate idea model
            if not self.generate_idea_model():
                return False
            
            # Step 5: Generate application
            if not self.generate_application():
                return False
            
            # Offer deployment
            self.console.print()
            if self._confirm("Would you like to deploy your app now?"):
                self.console.print()
                self.console.print(f"[cyan]Run:[/cyan] nexusai deploy {self.context.output_path}")
                self.console.print("[dim]Deployment will push to Vercel (frontend) + Render (backend)[/dim]")
            
            self.console.print()
            self.console.print("[bold cyan]Thank you for using LaunchForge![/bold cyan]")
            self.console.print("[dim]Build something amazing! 🚀[/dim]")
            self.console.print()
            
            return True
            
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Interrupted. Your progress has been saved.[/yellow]")
            return False
        except Exception as e:
            logger.exception("Assistant error")
            self.console.print(f"\n[red]Unexpected error: {e}[/red]")
            return False


# ============================================================================
# Quick Start Function
# ============================================================================

def run_build_assistant(
    llm_provider: str = "auto",
    output_dir: str = "./output",
    theme: str = "Modern",
    verbose: bool = False,
) -> bool:
    """
    Run the interactive build assistant.
    
    Args:
        llm_provider: LLM provider to use ('auto', 'perplexity', 'groq', 'mock')
        output_dir: Directory for generated output
        theme: Default UI theme
        verbose: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    assistant = InteractiveAssistant(
        llm_provider=llm_provider,
        output_dir=output_dir,
        theme=theme,
        verbose=verbose,
    )
    return assistant.run()


if __name__ == "__main__":
    # Allow running directly: python -m src.assistant
    success = run_build_assistant()
    sys.exit(0 if success else 1)

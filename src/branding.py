"""
Ignara - AI-Powered Startup Builder
Professional branding and CLI presentation.
"""

from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Version
VERSION = "1.0.0"

# Brand colors (for rich console)
BRAND_PRIMARY = "cyan"
BRAND_SECONDARY = "magenta"
BRAND_ACCENT = "yellow"
BRAND_SUCCESS = "green"

# ASCII Art Logo - Clean, professional
LOGO_ASCII = """
╦┌─┐┌┐┌┌─┐┬─┐┌─┐
║│ ┬│││├─┤├┬┘├─┤
╩└─┘┘└┘┴ ┴┴└─┴ ┴
"""

# Alternative compact logo
LOGO_COMPACT = "⚡ Ignara"

# Taglines
TAGLINE = "AI-Powered Startup Builder"
TAGLINE_FULL = "From idea to deployed app in minutes, not months."

# Product description
DESCRIPTION = """
Ignara uses AI with real-time web intelligence to:
• Discover validated market opportunities
• Generate production-ready applications
• Deploy to cloud with one command
"""

# Feature highlights for CLI
FEATURES = [
    ("🔍", "Market Intelligence", "Real-time pain point discovery via Perplexity AI"),
    ("💡", "Smart Ideation", "AI-generated ideas scored by market demand"),
    ("⚡", "Instant Apps", "Full-stack code in minutes, not months"),
    ("🚀", "One-Click Deploy", "Push to Render, Vercel, or Railway"),
]


def get_banner(include_tagline: bool = True, include_version: bool = True) -> str:
    """Get the ASCII banner for CLI display."""
    lines = [LOGO_ASCII.strip()]

    if include_tagline:
        lines.append(f"  {TAGLINE}")

    if include_version:
        lines.append(f"  v{VERSION}")

    return "\n".join(lines)


def print_banner(console: Optional[Console] = None):
    """Print a professional branded banner."""
    if console is None:
        console = Console()

    # Create styled logo
    logo_text = Text()
    logo_text.append(LOGO_ASCII.strip(), style=f"bold {BRAND_PRIMARY}")

    # Create panel with logo and tagline
    content = Text()
    content.append(LOGO_ASCII.strip(), style=f"bold {BRAND_PRIMARY}")
    content.append("\n\n")
    content.append(f"  {TAGLINE}", style=f"italic {BRAND_SECONDARY}")
    content.append("  │  ", style="dim")
    content.append(f"v{VERSION}", style="dim")

    panel = Panel(
        content,
        box=box.DOUBLE,
        border_style=BRAND_PRIMARY,
        padding=(0, 2),
    )

    console.print(panel)


def print_welcome(console: Optional[Console] = None):
    """Print welcome message with features."""
    if console is None:
        console = Console()

    print_banner(console)

    console.print()
    console.print(f"  [dim]{TAGLINE_FULL}[/dim]")
    console.print()

    for emoji, title, desc in FEATURES:
        console.print(f"  {emoji} [bold]{title}[/bold]: [dim]{desc}[/dim]")

    console.print()


def print_success_banner(app_name: str, output_path: str, console: Optional[Console] = None):
    """Print success banner after generation."""
    if console is None:
        console = Console()

    content = Text()
    content.append("✅ ", style="green")
    content.append("Successfully generated ", style="white")
    content.append(app_name, style=f"bold {BRAND_PRIMARY}")
    content.append("\n\n", style="white")
    content.append("📁 Output: ", style="dim")
    content.append(output_path, style="cyan")
    content.append("\n\n", style="white")
    content.append("Next steps:\n", style="bold")
    content.append(f"  cd {output_path}\n", style="dim")
    content.append("  ./scripts/deploy.sh  ", style="dim")
    content.append("# Deploy to cloud", style="dim italic")

    panel = Panel(
        content,
        title="[bold green]🚀 Launch Complete[/bold green]",
        box=box.ROUNDED,
        border_style="green",
        padding=(1, 2),
    )

    console.print(panel)


def print_step(step_num: int, total_steps: int, title: str, console: Optional[Console] = None):
    """Print a pipeline step header."""
    if console is None:
        console = Console()

    console.print()
    console.print(
        f"[bold {BRAND_PRIMARY}]━━━ Step {step_num}/{total_steps}: {title} ━━━[/bold {BRAND_PRIMARY}]"
    )


def get_cli_help_text() -> str:
    """Get help text for CLI."""
    return f"""
{LOGO_COMPACT} - {TAGLINE}

{TAGLINE_FULL}

QUICK START:
  ignara generate --demo           # Try with sample data
  ignara generate --llm-provider perplexity  # Use real AI

EXAMPLES:
  ignara generate -o ./my-startup  # Custom output directory
  ignara generate --deploy         # Generate and deploy
  ignara providers                 # List available AI providers

API KEYS:
  PERPLEXITY_API_KEY  - Primary (real-time web search)
  GROQ_API_KEY        - Backup (fast inference)

Get Perplexity key: https://www.perplexity.ai/settings/api
Get Groq key: https://console.groq.com/keys
"""


# Quick access
def logo() -> str:
    return LOGO_ASCII.strip()

def tagline() -> str:
    return TAGLINE

def version() -> str:
    return VERSION

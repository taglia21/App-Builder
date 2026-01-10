
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.theme import Theme
from rich import print as rprint
import time
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# Custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "title": "bold magenta",
    "step": "bold blue"
})

console = Console(theme=custom_theme)

class UI:
    """
    Centralized UI handler for the CLI using Rich.
    """
    
    @staticmethod
    def header(title: str, subtitle: str = ""):
        console.print()
        console.print(Panel(f"[bold white]{subtitle}[/]", title=f"[title]{title}[/]", border_style="magenta", expand=False))
        console.print()

    @staticmethod
    def success(message: str):
        console.print(f"[success]✓ {message}[/]")

    @staticmethod
    def error(message: str):
        console.print(f"[error]✗ {message}[/]")
    
    @staticmethod
    def info(message: str):
        console.print(f"[info]ℹ {message}[/]")
        
    @staticmethod
    def warning(message: str):
        console.print(f"[warning]⚠ {message}[/]")
        
    @staticmethod
    def step(message: str):
        console.print(f"\n[step]➤ {message}[/]")

    @staticmethod
    def prompt(text: str, default: str = None) -> str:
        return Prompt.ask(f"[bold cyan]{text}[/]", default=default)

    @staticmethod
    def confirm(text: str, default: bool = True) -> bool:
        return Confirm.ask(f"[bold cyan]{text}[/]", default=default)

    @staticmethod
    def table(title: str, columns: List[str], rows: List[List[str]]):
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        console.print(table)

    @staticmethod
    @contextmanager
    def spinner(text: str):
        with console.status(f"[bold blue]{text}...", spinner="dots"):
            yield

    @staticmethod
    @contextmanager
    def progress_bar():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            yield progress
